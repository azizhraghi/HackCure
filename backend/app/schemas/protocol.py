from pydantic import BaseModel, Field
from typing import List, Optional

class MedicationSchema(BaseModel):
    dci: str = Field(description="DCI (Dénomination Commune Internationale) of the medication")
    dosage: str = Field(description="Dosage amount and unit (e.g., '1 g', '200 mg')")
    frequency: str = Field(description="Frequency of intake (e.g., '3 fois par jour')")
    duration: Optional[str] = Field(None, description="Duration of treatment, if specified")
    instructions: Optional[str] = Field(None, description="Special instructions like 'au milieu du repas'")

class ExtractedProtocol(BaseModel):
    medications: List[MedicationSchema] = Field(default_factory=list, description="List of medications extracted from the document")
    general_instructions: Optional[str] = Field(None, description="General instructions, warnings or restrictions")
    confidence: str = Field(description="Confidence of extraction: 'explicit', 'inferred', or 'missing'")
