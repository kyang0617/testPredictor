import os
import numpy as np
import joblib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

from app.models import Entry
from app.embedding import embed_text

DATABASE_URL = os.environ["DATABASE_URL"]
MODEL_PATH = os.getenv("MODEL_PATH", "/app/model.joblib")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")

engine = create_engine(DATABASE_URL, future = True)
SessionLocal = sessionmaker(bind = engine, autoflush = False, autocommit = False, future = True)

def feature_row(entry: Entry, prev1, mean3, count_prev, embedding):
    base = [
        entry.confidence,
        entry.sleep,
        entry.stress,
        entry.hours_studied,
        prev1,
        mean3,
        float(count_prev),
    ]
    
    if embedding is None:
        emb = [0.0] * 384
    else:
        emb = embedding
    return np.array(base+emb, dtype=float)

def main():
    db = SessionLocal()
    try:
        labeled = (
            db.query(Entry)
            .filter(Entry.score.isnot(None))
            .order_by(Entry.user_id.asc(), Entry.test_id.asc(), Entry.created_at.asc())
            .all()
        )
        if len(labeled) < 5:
            raise SystemExit(f"Not enough labeled rows to train (have {len(labeled)}). Add more and label them.")

        X_list = []
        y_list = []
        
        history = {}
        
        for e in labeled:
            key = (e.user_id, e.test_id)
            past = history.get(key, [])
            
            prev1 = past[-1] if len(past) >= 1 else None
            mean3 = float(np.mean(past[-3:])) if len(past) >= 1 else None
            count_prev = len(past)
            
            embedding = e.feeling_embedding
            if embedding is None:
                embedding = embed_text(e.feeling_text, model_name=EMBEDDING_MODEL_NAME)

            X_list.append(feature_row(e, prev1, mean3, count_prev, embedding))
            y_list.append(float(e.score))
            
            past.append(float(e.score))
            history[key] = past
            
        X = np.vstack(X_list)
        y = np.array(y_list, dtype = float)
        
        model = Pipeline([
            ("imputer", SimpleImputer(strategy = "median")),
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("ridge", Ridge(alpha=1.0)),
        ])
        
        model.fit(X, y)
        
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        print(f"✅ Trained model on {len(y)} rows and saved to {MODEL_PATH}")
    finally:
        db.close()
        
if __name__ == "__main__":
    main()