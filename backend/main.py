"""SurgiGuard AI — minimal backend (FastAPI).

For now it only proxies the patient's Recovery Assistant chat to Mistral,
so the API key never ships inside the mobile app. The recovery plan below is
the fictional demo patient (Sarah Miller) used by the app.
"""

import os
import re

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mistralai.client import Mistral
from pydantic import BaseModel, Field

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

from app.api.v1 import router as api_router
from app.database import engine, Base
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="SurgiGuard AI backend", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(api_router, prefix="/v1")

@app.get("/health")
def health():
    return {"status": "ok", "llm": "mistral", "model": MISTRAL_MODEL, "v2": True}

