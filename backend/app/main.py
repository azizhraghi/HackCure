"""SurgiGuard AI backend: FastAPI app, routers and scheduler."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import db, scheduler
from .agents import digest, investigation  # noqa: F401  (registers the runner jobs)
from .config import settings
from .routers import (alerts, caregiver, chat, checkin, demo, investigations, medications, observations,
                      patients)
from d3_demo import router as d3_demo_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
BACKEND_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.engine()
    with db.session_scope() as repo:
        if repo.patient("sarah") is None:
            from seed.demo_seed import load
            load(repo)
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="SurgiGuard AI backend", version="0.2.0", lifespan=lifespan,
              description="Agentic post-operative surveillance prototype (FICTIONAL data, not a medical device).")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static/photos", StaticFiles(directory=BACKEND_DIR / "seed" / "photos"), name="photos")
(BACKEND_DIR / "uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=BACKEND_DIR / "uploads"), name="uploads")
# Preserve the existing React Native patient UI at /app; expose the teammate's
# patient/family/clinic dashboard at /agent-demo for inspecting the agent workflow.
PATIENT_WEB = BACKEND_DIR.parent / "mobile" / "dist-web"
app.mount("/app", StaticFiles(directory=PATIENT_WEB, html=True, check_dir=False), name="patient-web-preview")
app.mount("/agent-demo", StaticFiles(directory=BACKEND_DIR / "web", html=True), name="agent-dashboard")
app.include_router(d3_demo_router)


@app.get("/demo", include_in_schema=False)
def d3_demo_page():
    return FileResponse(BACKEND_DIR / "web_demo.html")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/app/")

for r in (chat, patients, observations, checkin, investigations, alerts, medications, caregiver, demo):
    app.include_router(r.router)


@app.get("/health")
def health():
    from .llm import route
    prov = settings.llm_provider
    return {"status": "ok", "llm": prov, "llm_mode": settings.llm_mode,
            "model": getattr(settings, f"{prov}_model", settings.mistral_model),
            "configured": bool(getattr(settings, f"{prov}_api_key", "")),
            "routes": {a: "/".join(route(a)) for a in ("investigation", "checkin_clarify", "digest", "chat")}}
