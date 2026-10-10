import os
import re
import math
from typing import List, Optional
from dotenv import load_dotenv

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import settings, get_embeddings

embeddings = get_embeddings()
VECTORSTORE_PATH = settings.VECTORSTORE_PATH


# =====================================================================
# SEMANTIC CHUNKING FOR MEDICAL DOCUMENTS
# =====================================================================

def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two embedding vectors."""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def _split_into_sentences(text: str) -> List[str]:
    """
    Split text into clean sentences or bullet-point clauses,
    preserving medical abbreviations (e.g. Dr., J1, J14, mg, etc.).
    """
    # Split on newlines, bullet points, or sentence terminals (. ! ?)
    raw_lines = text.split("\n")
    sentences: List[str] = []

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        # If it's a bullet item or section title, treat as separate semantic unit
        if line.startswith(("-", "*", "•", "#", "1.", "2.", "3.", "4.", "5.")):
            sentences.append(line)
        else:
            # Split by punctuation while keeping meaningful sentence units
            parts = re.split(r'(?<=[.!?])\s+', line)
            for p in parts:
                p_clean = p.strip()
                if p_clean:
                    sentences.append(p_clean)

    return sentences


class SemanticMedicalChunker:
    """
    Chunks medical text based on semantic boundaries rather than arbitrary character count.
    
    1. Splits text into discrete clinical propositions / sentences.
    2. Embeds consecutive sentences to measure topic drift (cosine distance).
    3. Breaks chunks when topic shifts significantly (distance > threshold) or max length is reached.
    4. Preserves all metadata (e.g. access_scope, source, procedure) for role-based retrieval.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.72,
        max_chunk_chars: int = 500,
        min_chunk_chars: int = 60,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_chunk_chars = max_chunk_chars
        self.min_chunk_chars = min_chunk_chars

    def split_text(self, text: str) -> List[str]:
        sentences = _split_into_sentences(text)
        if len(sentences) <= 1:
            return [text] if text.strip() else []

        # Try semantic embedding distance if API key is present
        if settings.MISTRAL_API_KEY:
            try:
                embeddings_list = embeddings.embed_documents(sentences)
                chunks: List[str] = []
                current_chunk_sentences: List[str] = [sentences[0]]
                current_chars = len(sentences[0])

                for i in range(1, len(sentences)):
                    sim = _cosine_similarity(embeddings_list[i - 1], embeddings_list[i])
                    sentence_len = len(sentences[i])

                    # Check if there is a semantic breakpoint or buffer is full
                    should_split = (
                        (sim < self.similarity_threshold and current_chars >= self.min_chunk_chars)
                        or (current_chars + sentence_len > self.max_chunk_chars)
                    )

                    if should_split:
                        chunks.append(" ".join(current_chunk_sentences))
                        current_chunk_sentences = [sentences[i]]
                        current_chars = sentence_len
                    else:
                        current_chunk_sentences.append(sentences[i])
                        current_chars += sentence_len + 1

                if current_chunk_sentences:
                    chunks.append(" ".join(current_chunk_sentences))

                return chunks
            except Exception:
                # Fallback to structural sentence-window chunker if embedding fails
                pass

        # Rule-based fallback (preserving medical bullet points and paragraphs)
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for s in sentences:
            if current and (current_len + len(s) > self.max_chunk_chars):
                chunks.append(" ".join(current))
                current = [s]
                current_len = len(s)
            else:
                current.append(s)
                current_len += len(s) + 1

        if current:
            chunks.append(" ".join(current))

        return chunks

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split a list of documents into semantic chunks while propagating metadata."""
        chunked_docs: List[Document] = []

        for doc in documents:
            text = doc.page_content
            chunks = self.split_text(text)

            for idx, chunk_text in enumerate(chunks):
                new_metadata = dict(doc.metadata)
                new_metadata["chunk_index"] = idx
                new_metadata["total_chunks"] = len(chunks)
                chunked_docs.append(Document(page_content=chunk_text, metadata=new_metadata))

        return chunked_docs


# Global instance of semantic chunker
semantic_chunker = SemanticMedicalChunker()


# =====================================================================
# FAISS STORE OPERATIONS
# =====================================================================

def get_vectorstore() -> FAISS:
    """Loads existing FAISS store or creates a new empty one."""
    if os.path.exists(VECTORSTORE_PATH) and os.listdir(VECTORSTORE_PATH):
        return FAISS.load_local(VECTORSTORE_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        # Create empty initial store
        return FAISS.from_texts(
            ["Initial empty document"],
            embeddings,
            metadatas=[{"access_scope": "none"}]
        )


def save_vectorstore(db: FAISS):
    """Persists FAISS index to disk."""
    os.makedirs(VECTORSTORE_PATH, exist_ok=True)
    db.save_local(VECTORSTORE_PATH)


def add_documents_to_store(documents: List[Document], use_semantic_chunking: bool = True):
    """
    Adds medical documents to FAISS with optional semantic chunking.
    Metadata like 'access_scope' is preserved for role-based retrieval.
    """
    if use_semantic_chunking:
        final_docs = semantic_chunker.split_documents(documents)
    else:
        final_docs = documents

    if not final_docs:
        return

    db = get_vectorstore()
    db.add_documents(final_docs)
    save_vectorstore(db)
