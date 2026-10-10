from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.ai.graphs.assistant_graph import assistant_graph
from app.ai.rag.retriever import Actor

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    actor = Actor(role=req.actor_role, granted_categories=req.granted_categories)
    
    # We only take the last message as query for simplicity in this MVP
    query = req.messages[-1].content if req.messages else ""
    messages_dicts = [{"role": m.role, "content": m.content} for m in req.messages[:-1]]
    
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
