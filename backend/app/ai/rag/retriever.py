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
        pass

    def retrieve(self, query: str, actor: Actor, k: int = 5) -> List[Document]:
        db = get_vectorstore()  # reloaded each time: passages may have been indexed since startup

        # Determine scope before retrieval
        if actor.role == "patient":
            allowed_scopes = ["protocol", "medications", "exercises", "warnings", "general_guidance"]
        elif actor.role == "caregiver":
            allowed_scopes = actor.granted_categories + ["general_guidance"]
        else:
            allowed_scopes = ["general_guidance"]

        def filter_func(metadata):
            return metadata.get("access_scope") in allowed_scopes and _same_patient(metadata, actor)

        try:
            docs = db.similarity_search(query, k=k*4, filter=filter_func)
        except Exception:
            docs = db.similarity_search(query, k=k*4)
            docs = [d for d in docs if d.metadata.get("access_scope") in allowed_scopes]

        # Double check no leak (scope and patient)
        safe_docs = [d for d in docs if d.metadata.get("access_scope") in allowed_scopes
                     and _same_patient(d.metadata, actor)]

        # Hybrid keyword relevance ranking (especially vital when using offline/fake embeddings)
        query_words = set(w.lower() for w in query.replace("?", " ").replace("!", " ").replace("'", " ").split() if len(w) > 3)
        if query_words and safe_docs:
            def score_doc(d: Document) -> int:
                text_lower = d.page_content.lower()
                return sum(1 for w in query_words if w in text_lower)

            safe_docs.sort(key=score_doc, reverse=True)

        return safe_docs[:k]


def _same_patient(metadata: dict, actor: Actor) -> bool:
    """Never mix patients: a passage tagged with another patient's id is excluded."""
    owner = metadata.get("patient_id")
    return owner is None or owner == actor.patient_id
