"""Recovery Assistant chat (moved from the original backend/main.py; same request/response shape).

Proxies to Mistral so the API key never ships inside the mobile app.
"""

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import settings

router = APIRouter(tags=["chat"])

RECOVERY_PLAN = """
PATIENT (fictional demo): Sarah Miller, 64. Total right knee replacement.
Today is day 3 after hospital discharge, of a 42-day recovery plan. Surgeon: Dr. Elena Ruiz, St. Joseph Medical Center.
Allergy: penicillin.

CLINICIAN-APPROVED MEDICATIONS
- Paracetamol 1 g at 08:00, 14:00, 20:00 (pain relief, max 4 g/day).
- Celecoxib 200 mg at 09:00 with food (anti-inflammatory).
- Pantoprazole 20 mg at 08:00 (protects the stomach).
- Enoxaparin 40 mg subcutaneous injection at 20:00 for 14 days (prevents blood clots).
- Cefuroxime 500 mg at 08:00, 14:00, 20:00 (antibiotic, not a penicillin).
- Do not take ibuprofen or other NSAIDs on top of celecoxib/enoxaparin unless the surgeon agrees.

ACTIVITY & REHABILITATION
- Weight bearing as tolerated with crutches for ~14 days.
- Knee bends 2 x 10 morning and evening, straight-leg raises 2 x 10, ankle pumps 3 x 15. Goal: 90° flexion by day 10, 110° by week 6.
- Ice 15-20 min after exercises. Keep the leg elevated when resting.
- No driving until cleared by the surgeon (usually around 4-6 weeks, and never while on strong painkillers).

WOUND CARE
- Waterproof dressing: showering is allowed with the dressing on; no bath, pool or soaking until staples are removed and the wound is fully closed.
- Do not touch or change the dressing unless instructed. A wound photo is requested daily in the app.

WARNING SIGNS (contact the surgeon's office the same day)
- Fever over 38°C, spreading redness, increasing warmth or swelling, drainage or bad smell from the wound, pain that keeps increasing.

EMERGENCY (call emergency services immediately)
- Sudden shortness of breath or chest pain (possible pulmonary embolism), calf pain/swelling in either leg, fainting.

APPOINTMENTS
- Physiotherapy in 6 days at 15:00, staple removal in 8 days at 09:00, follow-up with Dr. Ruiz in 12 days at 10:30.
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


class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=40)
    lang: str = "en"


class ChatResponse(BaseModel):
    reply: str
    escalate: bool


_client = None


def _mistral():
    global _client
    if _client is None and settings.mistral_api_key:
        from mistralai.client import Mistral
        _client = Mistral(api_key=settings.mistral_api_key)
    return _client


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    client = _mistral()
    if client is None:
        raise HTTPException(status_code=503, detail="MISTRAL_API_KEY is not set on the server")

    language = "French" if req.lang.lower().startswith("fr") else "English"
    messages = [{"role": "system", "content": SYSTEM_PROMPT.replace("{lang}", language)}]
    messages += [msg.model_dump() for msg in req.messages[-12:]]

    try:
        res = await client.chat.complete_async(model=settings.mistral_model, messages=messages, temperature=0.2,
                                               max_tokens=400)
    except Exception as exc:  # network / auth / quota errors
        raise HTTPException(status_code=502, detail=f"Mistral error: {exc}") from exc

    content = res.choices[0].message.content if res.choices else ""
    if isinstance(content, list):  # content chunks
        content = "".join(getattr(c, "text", "") for c in content)
    text = (content or "").strip()
    escalate = "[ESCALATE]" in text
    text = re.sub(r"\s*\[ESCALATE\]\s*", " ", text).strip()
    return ChatResponse(reply=text, escalate=escalate)
