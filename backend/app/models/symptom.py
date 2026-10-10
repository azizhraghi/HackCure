from sqlalchemy import Column, String, Integer, DateTime, JSON
from datetime import datetime
from app.database import Base

class SymptomReport(Base):
    __tablename__ = "symptom_reports"

    id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, index=True)
    reporter_id = Column(String) # could be caregiver
    raw_text = Column(String, nullable=True)
    emoji_code = Column(String, nullable=True)
    pain_score = Column(Integer, nullable=True)
    extraction_status = Column(String) # pending, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

class SymptomItem(Base):
    __tablename__ = "symptom_items"

    id = Column(String, primary_key=True, index=True)
    report_id = Column(String, index=True)
    symptom_code = Column(String) # e.g. "fever", "nausea"
    assertion = Column(String) # "present", "absent", "unknown"
    severity = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
