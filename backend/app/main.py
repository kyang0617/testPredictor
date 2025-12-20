from fastapi import FastAPI, Depends
from typing import Optional, List
from sqlalchemy.orm import Session

from .db import Base, engine, get_db, wait_for_db
from .models import Entry
from .schemas import EntryCreate, EntryOut

app = FastAPI(title="Backend API")

@app.on_event("startup")
def on_startup():
    wait_for_db()
    Base.metadata.create_all(bind = engine)
    

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/entries", response_model = EntryOut)
def create_entry(payload: EntryCreate, db: Session = Depends(get_db)):
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    row = Entry(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

@app.get("/entries", response_model = List[EntryOut])
def list_entries(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Entry).order_by(Entry.created_at.desc())
    if user_id is not None:
        q = q.filter(Entry.user_id == user_id)
    return q.limit(50).all()