from typing import List
from langchain_core.documents import Document
from app.ai.rag.vectorstore import get_vectorstore

class Actor:
    def __init__(self, role: str, granted_categories: List[str] = None):
        self.role = role
        self.granted_categories = granted_categories or []

class ScopedRetriever:
    def __init__(self):
        self.db = get_vectorstore()

    def retrieve(self, query: str, actor: Actor, k: int = 5) -> List[Document]:
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
            return metadata.get("access_scope") in allowed_scopes

        try:
            docs = self.db.similarity_search(query, k=k, filter=filter_func)
        except Exception:
            # Fallback if filter_func fails with older FAISS versions
            docs = self.db.similarity_search(query, k=k*3)
            docs = [d for d in docs if d.metadata.get("access_scope") in allowed_scopes][:k]
            
        # Double check no leak
        safe_docs = [d for d in docs if d.metadata.get("access_scope") in allowed_scopes]
        return safe_docs
