from pydantic import BaseModel, Field
from typing import List, Optional

class SymptomExtractionItem(BaseModel):
    symptom_code: str = Field(description="Standardized code or name for the symptom, e.g., 'fever', 'nausea', 'wound_pain'")
    assertion: str = Field(description="'present', 'absent', or 'unknown'")
    severity: Optional[str] = Field(None, description="Severity if mentioned, e.g., 'mild', 'moderate', 'severe'")
    onset: Optional[str] = Field(None, description="When did it start if mentioned")

class SymptomExtractionResult(BaseModel):
    items: List[SymptomExtractionItem] = Field(default_factory=list, description="Extracted symptoms")
    warning_flag: bool = Field(default=False, description="True if any extracted symptom is a red flag (e.g. fever, chest pain)")
