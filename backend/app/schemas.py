from typing import Optional
from datetime import datetime
from pydantic import BaseModel

try:
    from pydantic import ConfigDict
    _V2 = True
except Exception:
    _V2 = False
    
    
class EntryCreate(BaseModel):
    user_id: int
    test_id: int
    score: Optional[float] = None
    confidence: Optional[float] = None
    stress: Optional[float] = None
    sleep: Optional[float] = None
    hours_studied: Optional[float] = None
    feeling_text: Optional[str] = None
    score: Optional[float] = None
    

class EntryLabelUpdate(BaseModel):
    score: float
    
    
class EntryOut(EntryCreate):
    id: int
    user_id: int
    test_id: int
    score: Optional[float] = None
    predicted_score: Optional[float] = None
    confidence: Optional[float] = None
    stress: Optional[float] = None
    sleep: Optional[float] = None
    hours_studied: Optional[float] = None
    feeling_text: Optional[str] = None
    created_at: datetime
    
    if _V2:
        model_config = ConfigDict(from_attributes = True)
    else:
        class Config:
            orm_mode = True
            

class TrainRequest(BaseModel):
    user_id: int
    test_id: int

class TrainStatusResponse(BaseModel):
    user_id: int
    test_id: int
    labeled_count: int
    min_required: int
    can_train: bool
    model_exists: bool
    trained_rows: int
    needs_retrain: bool

class TrainResponse(BaseModel):
    user_id: int
    test_id: int
    trained_rows: int
    train_mae: float
    model_path: str

class PredictRequest(EntryCreate):
    pass

class PredictResponse(BaseModel):
    entry_id: int
    predicted_score: float