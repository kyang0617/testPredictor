import os
from typing import Optional, List, Tuple

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import joblib
import numpy as np

from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

from .db import Base, engine, get_db, wait_for_db
from .models import Entry
from .schemas import (
    EntryCreate, EntryOut, EntryLabelUpdate,
    PredictRequest, PredictResponse,
    TrainRequest, TrainStatusResponse, TrainResponse,  # <- add these to schemas.py
)
from .embedding import embed_text

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
MODEL_DIR = os.getenv("MODEL_DIR", "/app/models")
MIN_TRAIN_ROWS = int(os.getenv("MIN_TRAIN_ROWS", "10"))  # minimum labeled rows required (score != None)

# Cache: (user_id, test_id) -> (model, mtime)
_model_cache = {}


def model_path_for(user_id: int, test_id: int) -> str:
    os.makedirs(MODEL_DIR, exist_ok=True)
    return os.path.join(MODEL_DIR, f"model_u{user_id}_t{test_id}.joblib")


def labeled_count(db: Session, user_id: int, test_id: int) -> int:
    return (
        db.query(Entry)
        .filter(Entry.user_id == user_id, Entry.test_id == test_id, Entry.score.isnot(None))
        .count()
    )


def load_model(user_id: int, test_id: int):
    path = model_path_for(user_id, test_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=503, detail=f"Model not found at {path}. Train it first.")

    mtime = os.path.getmtime(path)
    key = (user_id, test_id)
    cached = _model_cache.get(key)

    if cached is None or cached[1] != mtime:
        _model_cache[key] = (joblib.load(path), mtime)

    return _model_cache[key][0]

def trained_rows_from_model(model) -> int:
    return int(getattr(model, "trained_rows_", 0))

def prev_score_features(db: Session, user_id: int, test_id: int) -> Tuple[Optional[float], Optional[float], int]:
    """For prediction: use up to last 3 labeled scores for same (user_id, test_id)."""
    rows = (
        db.query(Entry)
        .filter(Entry.user_id == user_id, Entry.test_id == test_id, Entry.score.isnot(None))
        .order_by(Entry.created_at.desc())
        .limit(3)
        .all()
    )

    if not rows:
        return None, None, 0

    scores = [r.score for r in rows if r.score is not None]
    prev1 = scores[0] if len(scores) >= 1 else None
    mean3 = float(np.mean(scores)) if scores else None
    count_prev = len(scores)
    return prev1, mean3, count_prev


def build_feature_vector(payload: EntryCreate, embedding: Optional[List[float]], prev1, mean3, count_prev) -> np.ndarray:
    """
    Must match training feature layout:
      [confidence, stress, sleep, hours_studied, prev1, mean3, count_prev] + embedding(384)
    """
    base = [
        payload.confidence,
        payload.stress,
        payload.sleep,
        payload.hours_studied,
        prev1,
        mean3,
        float(count_prev),
    ]
    emb = embedding if embedding is not None else [0.0] * 384
    return np.array(base + emb, dtype=float)


def train_model_for(db: Session, user_id: int, test_id: int) -> Tuple[int, float, str]:
    """
    Train a Ridge regression model for a specific (user_id, test_id) using labeled rows (score != None).
    Uses a rolling history so prev-score features don't leak the current label.
    """
    rows = (
        db.query(Entry)
        .filter(Entry.user_id == user_id, Entry.test_id == test_id, Entry.score.isnot(None))
        .order_by(Entry.created_at.asc())
        .all()
    )

    if len(rows) < MIN_TRAIN_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough labeled entries to train. Have {len(rows)}, need {MIN_TRAIN_ROWS}.",
        )

    X_list, y_list = [], []
    history_scores: List[float] = []

    for e in rows:
        prev1 = history_scores[-1] if len(history_scores) >= 1 else None
        mean3 = float(np.mean(history_scores[-3:])) if len(history_scores) >= 1 else None
        count_prev = len(history_scores)

        emb = e.feeling_embedding
        if emb is None:
            emb = embed_text(e.feeling_text, model_name=EMBEDDING_MODEL_NAME)

        base = [
            e.confidence,
            e.stress,
            e.sleep,
            e.hours_studied,
            prev1,
            mean3,
            float(count_prev),
        ]
        emb = emb if emb is not None else [0.0] * 384

        X_list.append(np.array(base + emb, dtype=float))
        y_list.append(float(e.score))

        history_scores.append(float(e.score))

    X = np.vstack(X_list)
    y = np.array(y_list, dtype=float)

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=1.0)),
    ])
    model.fit(X, y)

    model.trained_rows_ = int(len(y))
    joblib.dump(model, path)
    
    preds = model.predict(X)
    mae = float(mean_absolute_error(y, preds))

    path = model_path_for(user_id, test_id)
    model.trained_rows_ = int(len(y))
    joblib.dump(model, path)

    # refresh cache so next load pulls the new model
    _model_cache.pop((user_id, test_id), None)

    return len(y), mae, path


app = FastAPI(title="Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    wait_for_db()
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/entries", response_model=EntryOut)
def create_entry(payload: EntryCreate, db: Session = Depends(get_db)):
    emb = embed_text(payload.feeling_text, model_name=EMBEDDING_MODEL_NAME)
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()

    row = Entry(**data, feeling_embedding=emb)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.patch("/entries/{entry_id}", response_model=EntryOut)
def label_entry(entry_id: int, payload: EntryLabelUpdate, db: Session = Depends(get_db)):
    row = db.get(Entry, entry_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    row.score = payload.score
    db.commit()
    db.refresh(row)
    return row


@app.get("/entries", response_model=List[EntryOut])
def list_entries(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Entry).order_by(Entry.created_at.desc())
    if user_id is not None:
        q = q.filter(Entry.user_id == user_id)
    return q.limit(50).all()


@app.get("/train/status", response_model=TrainStatusResponse)
def train_status(user_id: int, test_id: int, db: Session = Depends(get_db)):
    path = model_path_for(user_id, test_id)
    count = labeled_count(db, user_id, test_id)

    if os.path.exists(path):
        m = load_model(user_id, test_id)
        trained_rows = trained_rows_from_model(m)
    else:
        trained_rows = 0

    return TrainStatusResponse(
        user_id=user_id,
        test_id=test_id,
        labeled_count=count,
        min_required=MIN_TRAIN_ROWS,
        can_train=(count >= MIN_TRAIN_ROWS),
        model_exists=os.path.exists(path),
        trained_rows=trained_rows,
        needs_retrain=(count > trained_rows),
    )



@app.post("/train", response_model=TrainResponse)
def train(req: TrainRequest, db: Session = Depends(get_db)):
    trained_rows, mae, path = train_model_for(db, req.user_id, req.test_id)
    return TrainResponse(
        user_id=req.user_id,
        test_id=req.test_id,
        trained_rows=trained_rows,
        train_mae=mae,
        model_path=path,
    )


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest, db: Session = Depends(get_db)):
    # requires a model for that user/test
    model = load_model(payload.user_id, payload.test_id)

    emb = embed_text(payload.feeling_text, model_name=EMBEDDING_MODEL_NAME)
    prev1, mean3, count_prev = prev_score_features(db, payload.user_id, payload.test_id)
    x = build_feature_vector(payload, emb, prev1, mean3, count_prev)

    pred = float(model.predict([x])[0])

    # store prediction request + prediction
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    row = Entry(**data, feeling_embedding=emb, predicted_score=pred, score=None)
    db.add(row)
    db.commit()
    db.refresh(row)

    return PredictResponse(entry_id=row.id, predicted_score=pred)
