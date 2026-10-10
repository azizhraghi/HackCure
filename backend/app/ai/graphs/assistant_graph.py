from typing import TypedDict, List
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import os
from app.ai.guardrails.input_sanitizer import sanitize_input
from app.ai.guardrails.output_validator import validate_output
from app.ai.rag.retriever import ScopedRetriever, Actor

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

class AssistantState(TypedDict):
    messages: List[dict]
    actor: Actor
    query: str
    cleaned_query: str
    threats: List[str]
    context_docs: List[str]
    raw_response: str
    final_response: str
    escalate: bool
    citations: List[str]

llm = ChatMistralAI(model=MISTRAL_MODEL, mistral_api_key=MISTRAL_API_KEY, temperature=0.1)

retriever = ScopedRetriever()

def sanitize_node(state: AssistantState):
    query = state["query"]
    cleaned, threats = sanitize_input(query)
    return {"cleaned_query": cleaned, "threats": threats}

def retrieve_node(state: AssistantState):
    if state["threats"]:
        # Block if injection detected
        return {"context_docs": []}
        
    docs = retriever.retrieve(state["cleaned_query"], state["actor"])
    # Format docs
    context_str = "\n\n".join([f"[Source {i+1}]: {d.page_content}" for i, d in enumerate(docs)])
    return {"context_docs": [context_str]}

def generate_node(state: AssistantState):
    if state["threats"]:
        return {"raw_response": "Je ne peux pas répondre à cette requête pour des raisons de sécurité."}
        
    context = state["context_docs"][0] if state["context_docs"] else "Aucune information disponible."
    
    prompt = f"""You are the SurgiGuard AI Recovery Assistant.
Answer ONLY from the CONTEXT below. If the answer is not in the context, say 'I don't have this information, please ask your care team.'
Cite your sources like [Source X].
Do not diagnose or change treatments. If uncertain or emergency, end with [ESCALATE].

CONTEXT:
{context}

USER QUERY:
{state["cleaned_query"]}
"""
    # Simply passing prompt as user message to LLM for now, plus history
    messages = state["messages"][-5:] + [{"role": "user", "content": prompt}]
    
    # Langchain expects list of dicts or BaseMessage. ChatMistralAI handles lists of dicts.
    try:
        response = llm.invoke(messages)
        return {"raw_response": response.content}
    except Exception as e:
        return {"raw_response": f"Erreur de génération: {str(e)}", "escalate": True}

def validate_node(state: AssistantState):
    raw = state.get("raw_response", "")
    final, esc, citations = validate_output(raw, state.get("context_docs", []))
    
    if state.get("escalate"):
        esc = True
        
    return {"final_response": final, "escalate": esc, "citations": citations}

builder = StateGraph(AssistantState)
builder.add_node("sanitize", sanitize_node)
builder.add_node("retrieve", retrieve_node)
builder.add_node("generate", generate_node)
builder.add_node("validate", validate_node)

builder.set_entry_point("sanitize")
builder.add_edge("sanitize", "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", "validate")
builder.add_edge("validate", END)

assistant_graph = builder.compile()
