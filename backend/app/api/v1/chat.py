from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.ai.graphs.assistant_graph import assistant_graph
from app.ai.rag.retriever import Actor

router = APIRouter()


def _patient_gate(req: ChatRequest, query: str):
    """Shared backend: the deterministic urgent rules (D3) run before any LLM, and the patient's active plan
    is indexed for retrieval. Returns an urgent ChatResponse, or None to continue with the RAG assistant."""
    from app import db, monitor
    from app.integrations import d2_bridge
    from app.models import ObservationIn
    from app.safety import urgent_rules
    with db.session_scope() as repo:
        if repo.patient(req.patient_id) is None:
            raise HTTPException(status_code=404, detail="unknown patient")
        plan = repo.plan(req.patient_id)
        if req.actor_role in ("patient", "caregiver") and urgent_rules.evaluate_answer(query, plan).urgent:
            source = "patient" if req.actor_role == "patient" else "caregiver_on_behalf"
            monitor.ingest(repo, ObservationIn(patient_id=req.patient_id, type="checkin", source=source,
                                               value={"comment": query, "channel": "assistant_v1"}))
            text = plan.get("patient_texts", {}).get("urgent", "Call emergency services now.")
            return ChatResponse(reply=text, escalate=True, citations=["urgent_rules"])
        try:
            d2_bridge.index_plan(repo, req.patient_id)
        except Exception:  # retrieval without the plan still answers from shared guidance
            pass
    return None


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    actor = Actor(role=req.actor_role, granted_categories=req.granted_categories, patient_id=req.patient_id)

    # We only take the last message as query for simplicity in this MVP
    query = req.messages[-1].content if req.messages else ""
    messages_dicts = [{"role": m.role, "content": m.content} for m in req.messages[:-1]]

    if req.patient_id:
        urgent = _patient_gate(req, query)
        if urgent:
            return urgent

    initial_state = {
        "messages": messages_dicts,
        "actor": actor,
        "query": query,
        "threats": [],
        "context_docs": [],
        "raw_response": "",
        "final_response": "",
        "escalate": False,
        "citations": []
    }

    try:
        # Run graph
        result = assistant_graph.invoke(initial_state)
        return ChatResponse(
            reply=result["final_response"],
            escalate=result["escalate"],
            citations=result["citations"]
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Assistant error: {str(exc)}")
