from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.documents import Document
from app.ai.rag.vectorstore import get_vectorstore

class Actor(BaseModel):
    role: str
    granted_categories: List[str] = Field(default_factory=list)
    patient_id: Optional[str] = None  # set: only this patient's passages (+ shared guidance without a patient_id)

class ScopedRetriever:
    def __init__(self):
        self.db = get_vectorstore()

    def retrieve(self, query: str, actor: Actor, k: int = 5) -> List[Document]:
        self.db = get_vectorstore()  # reload: passages may have been indexed since startup
        # Determine scope before retrieval
        if actor.role == "patient":
            allowed_scopes = ["protocol", "medications", "exercises", "warnings", "general_guidance"]
        elif actor.role == "caregiver":
            allowed_scopes = actor.granted_categories + ["general_guidance"]
        else:
            allowed_scopes = ["general_guidance"]
            
        # Retrieval with filter
        # FAISS in langchain supports metadata filtering via callable or dict
        def filter_func(metadata):
            return metadata.get("access_scope") in allowed_scopes and _same_patient(metadata, actor)

        try:
            docs = self.db.similarity_search(query, k=k, filter=filter_func)
        except Exception:
            # Fallback if filter_func fails with older FAISS versions
            docs = self.db.similarity_search(query, k=k*3)
            docs = [d for d in docs if d.metadata.get("access_scope") in allowed_scopes][:k]
            
        # Double check no leak
        safe_docs = [d for d in docs if d.metadata.get("access_scope") in allowed_scopes
                     and _same_patient(d.metadata, actor)]
        return safe_docs


def _same_patient(metadata: dict, actor: Actor) -> bool:
    """Never mix patients: a passage tagged with another patient's id is excluded."""
    owner = metadata.get("patient_id")
    return owner is None or owner == actor.patient_id
