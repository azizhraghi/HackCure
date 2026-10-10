from typing import TypedDict, List, Optional, Tuple, Any
import os
import re
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings, get_chat_llm
from app.ai.guardrails.input_sanitizer import sanitize_input
from app.ai.guardrails.output_validator import validate_output_with_reflection
from app.ai.rag.retriever import ScopedRetriever, Actor
from app.ai.graphs.symptom_graph import symptom_graph


# =====================================================================
# STATE DEFINITION (WITH MEMORY & SYMPTOM INTEGRATION)
# =====================================================================

class AssistantState(TypedDict):
    messages: List[dict]                  # Conversational history: [{"role": "user"|"assistant", "content": "..."}]
    actor: Actor                          # Role (patient / caregiver) with permissions
    query: str                            # Raw user message for this turn
    cleaned_query: str                    # Sanitized user query
    threats: List[str]                    # Injection threats detected
    context_docs: List[str]               # Retrieved RAG context chunks
    symptom_detected: bool                # True if message expresses symptoms/pain
    symptom_data: Optional[dict]          # Output from symptom_graph
    raw_response: str                     # Draft response before reflection
    final_response: str                   # Validated & self-reflected response
    reflection_notes: Optional[str]       # Notes from safety critic
    escalate: bool                        # Clinical escalation flag
    citations: List[str]                  # Citations [Source X]


# LLM instances: modular provider selection (Mistral or Groq)
llm = get_chat_llm(temperature=0.1)
critic_llm = get_chat_llm(temperature=0.0)

retriever = ScopedRetriever()


# =====================================================================
# SYMPTOM DETECTION HELPERS
# =====================================================================

SYMPTOM_KEYWORDS = [
    # French terms
    "douleur", "mal", "fièvre", "fievre", "chaud", "brûlure", "brulure",
    "rougeur", "gonflé", "gonflement", "œdème", "oedeme", "écoulement",
    "odeur", "pus", "saignement", "saigne", "essoufflement", "respirer",
    "poitrine", "thoracique", "mollet", "malaise", "vertige", "étourdissement",
    "nausée", "vomir", "fatigue", "raideur",
    # English terms
    "pain", "hurts", "fever", "burning", "redness", "swelling", "swollen",
    "drainage", "discharge", "odor", "bleeding", "shortness of breath",
    "chest pain", "calf", "fainting", "dizzy", "nausea", "vomit", "stiff"
]

def _detect_symptoms_in_query(query: str) -> Tuple[bool, int]:
    """
    Checks if the user query describes physical symptoms or mentions pain / EVA score.
    Returns (has_symptoms, detected_pain_score).
    """
    q_lower = query.lower()
    has_sym = any(kw in q_lower for kw in SYMPTOM_KEYWORDS)
    pain_score = 0

    # Match fraction pain score like "7/10" or "8 / 10"
    match_fraction = re.search(r"(\d{1,2})\s*/\s*10", q_lower)
    if match_fraction:
        try:
            pain_score = min(10, max(0, int(match_fraction.group(1))))
            has_sym = True
        except ValueError:
            pass
    else:
        # Match "douleur 8", "douleur de 7", "pain 6"
        match_pain = re.search(r"(?:douleur|pain)\s+(?:de\s+|à\s+|est\s+de\s+)?(\d{1,2})", q_lower)
        if match_pain:
            try:
                pain_score = min(10, max(0, int(match_pain.group(1))))
                has_sym = True
            except ValueError:
                pass

    return has_sym, pain_score


# =====================================================================
# GRAPH NODES
# =====================================================================

def sanitize_node(state: AssistantState):
    """Sanitize input against prompt injection and malicious HTML."""
    query = state.get("query", "")
    cleaned, threats = sanitize_input(query)
    return {"cleaned_query": cleaned, "threats": threats}


def symptom_check_node(state: AssistantState):
    """
    Dynamically routes to symptom_graph if the user query reports physical symptoms.
    Extracts structured symptoms, flags emergencies / warnings deterministically.
    """
    if state.get("threats"):
        return {"symptom_detected": False, "symptom_data": None}

    query = state.get("cleaned_query", state.get("query", ""))
    has_symptoms, pain_score = _detect_symptoms_in_query(query)

    if not has_symptoms:
        return {"symptom_detected": False, "symptom_data": None}

    # Dynamically invoke symptom_graph
    emoji_code = "very_unwell" if pain_score >= 8 else ("unwell" if pain_score >= 5 else "okay")
    symptom_input = {
        "raw_text": query,
        "emoji_code": emoji_code,
        "pain_score": pain_score,
        "deterministic_warning": False,
        "deterministic_emergency": False,
        "extracted_data": None,
        "errors": []
    }

    try:
        sym_result = symptom_graph.invoke(symptom_input)
        is_emergency = sym_result.get("deterministic_emergency", False)
        is_warning = sym_result.get("deterministic_warning", False)
        extracted = sym_result.get("extracted_data")
        extracted_dict = extracted.model_dump() if extracted and hasattr(extracted, "model_dump") else None

        escalate = is_emergency or is_warning or state.get("escalate", False)

        symptom_payload = {
            "is_emergency": is_emergency,
            "is_warning": is_warning,
            "extracted_data": extracted_dict,
            "pain_score": pain_score,
            "errors": sym_result.get("errors", [])
        }

        return {
            "symptom_detected": True,
            "symptom_data": symptom_payload,
            "escalate": escalate
        }
    except Exception as exc:
        return {
            "symptom_detected": True,
            "symptom_data": {"error": str(exc), "is_emergency": False, "is_warning": True},
            "escalate": True
        }


def retrieve_node(state: AssistantState):
    """Retrieves relevant documents with strict role-based access scoping."""
    if state.get("threats"):
        return {"context_docs": []}

    docs = retriever.retrieve(state["cleaned_query"], state["actor"])
    context_str = "\n\n".join([f"[Source {i+1}]: {d.page_content}" for i, d in enumerate(docs)])
    return {"context_docs": [context_str] if context_str else []}


def generate_node(state: AssistantState):
    """
    Generates response using conversational history, RAG context, and symptom evaluation.
    """
    if state.get("threats"):
        return {"raw_response": "Je ne peux pas répondre à cette requête pour des raisons de sécurité."}

    symptom_data = state.get("symptom_data") or {}

    # Fast-path for critical emergency symptoms (e.g. chest pain, pulmonary embolism signs)
    if symptom_data.get("is_emergency"):
        emergency_text = (
            "🚨 URGENCE MÉDICALE DÉTECTÉE : Les symptômes décrits (douleur thoracique, essoufflement "
            "ou malaise) représentent un signal d'urgence potentielle après votre chirurgie.\n\n"
            "Action immédiate requise :\n"
            "- Appelez immédiatement le SAMU (15) ou le 112, ou faites-vous conduire au service d'urgences le plus proche.\n"
            "- Ne restez pas seul(e) et prévenez un proche.\n"
            "- Ne prenez aucun nouveau médicament sans avis médical.\n\n"
            "[ESCALATE]"
        )
        return {"raw_response": emergency_text, "escalate": True}

    context = state["context_docs"][0] if state.get("context_docs") else "Aucune information spécifique disponible dans le protocole."

    # Build prompt with symptom awareness and strict clinical boundaries
    symptom_instruction = ""
    if symptom_data.get("is_warning"):
        symptom_instruction = (
            "\nATTENTION : Le patient rapporte un symptôme d'alerte ou une douleur importante. "
            "Rappelez-lui impérativement de contacter l'équipe du Dr. Ruiz dès aujourd'hui. "
            "Ne posez aucun diagnostic et terminez par [ESCALATE].\n"
        )

    system_instruction = f"""You are the SurgiGuard AI Recovery Assistant.
You accompany a recovering postoperative patient.
Answer ONLY from the CONTEXT provided below and authorized general post-op safety rules.
If information is missing from the context, state: 'Je n'ai pas cette information dans votre protocole, veuillez demander à votre équipe médicale.'

CRITICAL RULES:
- Never provide a medical diagnosis (e.g. do not say 'vous avez une infection' or 'vous êtes guéri').
- Never adjust medication doses or advise stopping/starting drugs.
- Cite sources whenever possible like [Source X].
- If symptoms require medical attention, end your response with [ESCALATE].
{symptom_instruction}
CONTEXT:
{context}
"""

    # Format multi-turn conversational memory
    history = state.get("messages", [])
    recent_history = history[-8:] if len(history) > 8 else history

    messages_payload: List[dict] = [{"role": "system", "content": system_instruction}]

    for m in recent_history:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role in ("user", "assistant") and content:
            messages_payload.append({"role": role, "content": content})

    # Add current query
    messages_payload.append({
        "role": "user",
        "content": state["cleaned_query"]
    })

    try:
        response = llm.invoke(messages_payload)
        return {"raw_response": response.content}
    except Exception as exc:
        err_msg = str(exc)
        if "429" in err_msg or "rate_limit" in err_msg.lower():
            safe_fallback = (
                "Le service d'assistance est temporairement très sollicité. "
                "Pour votre sécurité, si vous présentez des symptômes inhabituels ou douloureux, "
                "veuillez contacter directement votre équipe médicale. [ESCALATE]"
            )
            return {"raw_response": safe_fallback, "escalate": True}
        return {"raw_response": f"Service temporairement indisponible : {err_msg}", "escalate": True}


def validate_node(state: AssistantState):
    """
    Self-Reflection Node:
    1. Critic LLM re-evaluates the draft response to verify NO diagnosis or unapproved advice is present.
    2. Runs deterministic guardrails for forbidden phrases.
    3. Updates conversational history with the turn.
    """
    raw = state.get("raw_response", "")
    query = state.get("cleaned_query", state.get("query", ""))
    context_docs = state.get("context_docs", [])

    final, esc, citations, reflection_note = validate_output_with_reflection(
        text=raw,
        query=query,
        context_documents=context_docs,
        critic_llm=critic_llm
    )

    if state.get("escalate"):
        esc = True

    # Update conversational memory
    updated_messages = list(state.get("messages", []))
    updated_messages.append({"role": "user", "content": state.get("query", "")})
    updated_messages.append({"role": "assistant", "content": final})

    return {
        "final_response": final,
        "escalate": esc,
        "citations": citations,
        "reflection_notes": reflection_note,
        "messages": updated_messages
    }


# =====================================================================
# GRAPH COMPILATION WITH MEMORY SAVER
# =====================================================================

builder = StateGraph(AssistantState)
builder.add_node("sanitize", sanitize_node)
builder.add_node("symptom_check", symptom_check_node)
builder.add_node("retrieve", retrieve_node)
builder.add_node("generate", generate_node)
builder.add_node("validate", validate_node)

builder.set_entry_point("sanitize")
builder.add_edge("sanitize", "symptom_check")
builder.add_edge("symptom_check", "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", "validate")
builder.add_edge("validate", END)

# Memory checkpointer for multi-turn conversational persistence
memory = MemorySaver()
_compiled_assistant_graph = builder.compile(checkpointer=memory)


class AssistantGraphWrapper:
    """
    Wrapper ensuring assistant_graph.invoke works both with explicit thread_id config
    and in standalone single-turn calls (providing a default thread_id).
    """
    def __init__(self, inner_graph):
        self._graph = inner_graph

    def invoke(self, state: dict, config: Optional[dict] = None, **kwargs) -> dict:
        if config is None:
            config = {"configurable": {"thread_id": "default_session"}}
        elif "configurable" not in config or "thread_id" not in config["configurable"]:
            cfg = dict(config)
            cfg.setdefault("configurable", {})["thread_id"] = "default_session"
            config = cfg
        return self._graph.invoke(state, config=config, **kwargs)

    async def ainvoke(self, state: dict, config: Optional[dict] = None, **kwargs) -> dict:
        if config is None:
            config = {"configurable": {"thread_id": "default_session"}}
        elif "configurable" not in config or "thread_id" not in config["configurable"]:
            cfg = dict(config)
            cfg.setdefault("configurable", {})["thread_id"] = "default_session"
            config = cfg
        return await self._graph.ainvoke(state, config=config, **kwargs)

    def __getattr__(self, name):
        return getattr(self._graph, name)


assistant_graph = AssistantGraphWrapper(_compiled_assistant_graph)

