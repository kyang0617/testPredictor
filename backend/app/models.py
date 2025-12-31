from sqlalchemy import Column, Integer, Float, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from .db import Base

class Entry(Base):
    __tablename__ = "entries"
    
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer, nullable = False, index = True)
    test_id = Column(Integer, nullable = False, index = True)
    
    score = Column(Float, nullable = True)
    
    predicted_score = Column(Float, nullable=True)

    confidence = Column(Float, nullable = True)
    stress = Column(Float, nullable = True)
    sleep = Column(Float, nullable = True)
    hours_studied = Column(Float, nullable = True)
    feeling_text = Column(Text, nullable = True)
    
    feeling_embedding = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
