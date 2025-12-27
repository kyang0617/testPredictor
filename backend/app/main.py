import os
from typing import Optional, List, Tuple

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import joblib
import numpy as np

from .db import Base, engine, get_db, wait_for_db
from .models import Entry
from .schemas import (
    EntryCreate, EntryOut, EntryLabelUpdate,
    PredictRequest, PredictResponse
)
from .embedding import embed_text

MODEL_PATH = os.getenv("MODEL_PATH", "/app/model.joblib")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")

_model = None
_model_mtime = None

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

def get_model():
    global _model, _model_mtime
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code = 503, detail = f"Model not found at {MODEL_PATH}. Train it first.")
    mtime = os.path.getmtime(MODEL_PATH)
    if _model is None or _model_mtime != mtime:
        _model = joblib.load(MODEL_PATH)
        _model_mtime = mtime
    return _model


def prev_score_features(db: Session, user_id: int, test_id: int):
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


def build_feature_vector(payload: EntryCreate, embedding: Optional[List[float]], prev1, mean3, count_prev):
    base = [
        payload.confidence,
        payload.stress,
        payload.sleep,
        payload.hours_studied,
        prev1,
        mean3,
        float(count_prev),
    ]
    if embedding is None:
        emb = [0.0] * 384
    else:
        emb = embedding
    return np.array(base + emb, dtype=float)



@app.on_event("startup")
def on_startup():
    wait_for_db()
    Base.metadata.create_all(bind = engine)
    

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/entries", response_model = EntryOut)
def create_entry(payload: EntryCreate, db: Session = Depends(get_db)):
    emb = embed_text(payload.feeling_text, model_name=EMBEDDING_MODEL_NAME)
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()

    row = Entry(
        **data,
        feeling_embedding=emb,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

@app.patch("/entries/{entry_id}", response_model = EntryOut)
def label_entry(entry_id: int, payload: EntryLabelUpdate, db: Session = Depends(get_db)):
    row = db.get(Entry, entry_id)
    if row is None:
        raise HTTPException(status_code = 404, detail = "Entry Not Found")
    row.score = payload.score
    db.commit()
    db.refresh(row)
    return row

@app.get("/entries", response_model = List[EntryOut])
def list_entries(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Entry).order_by(Entry.created_at.desc())
    if user_id is not None:
        q = q.filter(Entry.user_id == user_id)
    return q.limit(50).all()

@app.post("/predict", response_model = List[EntryOut])
def predict(payload: PredictRequest, db: Session = Depends(get_db)):
    model = get_model()
    
    emb = embed_text(payload.feeling_text, model_name = EMBEDDING_MODEL_NAME)
    prev1, mean3, count_prev = prev_score_features(db, payload.user_id, payload.test_id)
    x = build_feature_vector(payload, emb, prev1, mean3, count_prev)
    
    pred = float(model.predict([x])[0])
    
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    row = Entry(
        **data, 
        feeling_embedding = emb,
        predicted_score = pred,
        score = None,
    )
    
    db.add(row)
    db.commit()
    db.refresh(row)
    
    return PredictResponse(entry_id = row.id, predicted_score = pred)