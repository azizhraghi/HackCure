from pydantic import BaseModel, Field
from typing import List, Optional

class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    actor_role: str = Field(default="patient", description="'patient' or 'caregiver'")
    granted_categories: List[str] = Field(default_factory=list, description="For caregivers, what scopes they can access")
    lang: str = "en"

class ChatResponse(BaseModel):
    reply: str
    escalate: bool
    citations: List[str] = Field(default_factory=list)
