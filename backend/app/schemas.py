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
    
    
class EntryOut(EntryCreate):
    id: int
    created_at: datetime
    
    if _V2:
        model_config = ConfigDict(from_attributes = True)
    else:
        class Config:
            orm_mode = True