from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean
from datetime import datetime
from app.database import Base

class Protocol(Base):
    __tablename__ = "protocols"

    id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, index=True)
    status = Column(String)  # draft, in_review, approved, active, superseded
    version = Column(Integer)
    content_hash = Column(String)
    content = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Approval(Base):
    __tablename__ = "protocol_approvals"
    
    id = Column(String, primary_key=True, index=True)
    protocol_id = Column(String, index=True)
    approver_id = Column(String)
    content_hash = Column(String) # ensures approval matches exactly
    approved_at = Column(DateTime, default=datetime.utcnow)
