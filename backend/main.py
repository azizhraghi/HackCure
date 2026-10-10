"""SurgiGuard AI prototype backend: chat proxy and synthetic D3 demo routes."""

import os
import re

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from mistralai.client import Mistral
from pydantic import BaseModel, Field

from d3_demo import router as d3_demo_router

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

RECOVERY_PLAN = """
PATIENT (fictional demo): Sarah Miller, 64. Total right knee replacement on June 4, 2025.
Today is post-operative day 6 of a 42-day recovery plan. Surgeon: Dr. Elena Ruiz, St. Joseph Medical Center.
Allergy: penicillin.

CLINICIAN-APPROVED MEDICATIONS
- Paracetamol 1 g at 08:00, 14:00, 20:00 (pain relief, max 4 g/day).
- Celecoxib 200 mg at 09:00 with food (anti-inflammatory).
- Pantoprazole 20 mg at 08:00 (protects the stomach).
- Enoxaparin 40 mg subcutaneous injection at 20:00 for 14 days (prevents blood clots).
- Do not take ibuprofen or other NSAIDs on top of celecoxib/enoxaparin unless the surgeon agrees.

ACTIVITY & REHABILITATION
- Weight bearing as tolerated with crutches for ~14 days.
- Knee bends 2 x 10 morning and evening, straight-leg raises 2 x 10, ankle pumps 3 x 15. Goal: 90° flexion by day 10, 110° by week 6.
- Ice 15-20 min after exercises. Keep the leg elevated when resting.
- No driving until cleared by the surgeon (usually around 4-6 weeks, and never while on strong painkillers).

WOUND CARE
- Waterproof dressing: showering is allowed with the dressing on; no bath, pool or soaking until staples are removed (day 14) and the wound is fully closed.
- Do not touch or change the dressing unless instructed. A wound photo is requested daily in the app.

WARNING SIGNS (contact the surgeon's office the same day)
- Fever over 38°C, spreading redness, increasing warmth or swelling, drainage or bad smell from the wound, pain that keeps increasing.

EMERGENCY (call emergency services immediately)
- Sudden shortness of breath or chest pain (possible pulmonary embolism), calf pain/swelling in either leg, fainting.

APPOINTMENTS
- Physiotherapy June 12 15:00, staple removal June 14 09:00, follow-up with Dr. Ruiz June 18 10:30.
"""

SYSTEM_PROMPT = f"""You are the SurgiGuard AI Recovery Assistant inside a postoperative recovery app.
You help the patient understand their clinician-approved recovery plan, discharge instructions,
medications and exercises. Use ONLY the plan below and well-established general post-operative guidance.

Rules:
- You do not diagnose, and you never change doses or the plan. Medical decisions stay with the care team.
- Be warm, clear and short (max ~120 words). Use simple language. Use the patient's language: {{lang}}.
- If the question mentions a WARNING SIGN, tell them to contact Dr. Ruiz's office today.
- If it mentions an EMERGENCY symptom, tell them to call emergency services now, first, before anything else.
- If the answer is not in the plan, say so and suggest asking the care team.
- When professional assessment is needed, end your answer with the exact tag [ESCALATE].

{RECOVERY_PLAN}
"""

app = FastAPI(title="SurgiGuard AI backend", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(d3_demo_router)

client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None


class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=40)
    lang: str = "en"


class ChatResponse(BaseModel):
    reply: str
    escalate: bool


@app.get("/health")
def health():
    return {"status": "ok", "llm": "mistral", "model": MISTRAL_MODEL, "configured": client is not None}


@app.get("/demo", include_in_schema=False)
def demo_page():
    return FileResponse(os.path.join(os.path.dirname(__file__), "web_demo.html"))


app.mount("/app", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "mobile", "dist-web"), html=True), name="patient-web-preview")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if client is None:
        raise HTTPException(status_code=503, detail="MISTRAL_API_KEY is not set on the server")

    language = "French" if req.lang.lower().startswith("fr") else "English"
    messages = [{"role": "system", "content": SYSTEM_PROMPT.replace("{lang}", language)}]
    messages += [m.model_dump() for m in req.messages[-12:]]

    try:
        res = await client.chat.complete_async(model=MISTRAL_MODEL, messages=messages, temperature=0.2, max_tokens=400)
    except Exception as exc:  # network / auth / quota errors
        raise HTTPException(status_code=502, detail=f"Mistral error: {exc}") from exc

    content = res.choices[0].message.content if res.choices else ""
    if isinstance(content, list):  # content chunks
        content = "".join(getattr(c, "text", "") for c in content)
    text = (content or "").strip()
    escalate = "[ESCALATE]" in text
    text = re.sub(r"\s*\[ESCALATE\]\s*", " ", text).strip()
    return ChatResponse(reply=text, escalate=escalate)
