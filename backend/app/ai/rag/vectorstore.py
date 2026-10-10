from langchain_community.vectorstores import FAISS
from langchain_mistralai import MistralAIEmbeddings
from langchain_core.documents import Document
import os
from dotenv import load_dotenv

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

# Using mistral-embed
embeddings = MistralAIEmbeddings(mistral_api_key=MISTRAL_API_KEY)

VECTORSTORE_PATH = "./data/vectorstore"

def get_vectorstore():
    if os.path.exists(VECTORSTORE_PATH) and os.listdir(VECTORSTORE_PATH):
        return FAISS.load_local(VECTORSTORE_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        # Create empty
        return FAISS.from_texts(["Initial empty document"], embeddings, metadatas=[{"access_scope": "none"}])

def save_vectorstore(db: FAISS):
    os.makedirs(VECTORSTORE_PATH, exist_ok=True)
    db.save_local(VECTORSTORE_PATH)

def add_documents_to_store(documents: list[Document]):
    db = get_vectorstore()
    db.add_documents(documents)
    save_vectorstore(db)
