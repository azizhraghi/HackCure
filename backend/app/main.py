"""SurgiGuard AI backend: FastAPI app, routers and scheduler."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import db, scheduler
from .agents import digest, investigation, protocol  # noqa: F401  (registers the runner jobs)
from .config import settings
from .routers import (account_context, alerts, caregiver, chat, checkin, demo, documents, integration, investigations, medications,
                      observations, patients, wounds, hub, motor)
from d3_demo import router as d3_demo_router
from .api.v1 import router as d2_router  # Developer 2: documents (D2A), RAG assistant (D2B), check-in rules

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
BACKEND_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.engine()
    with db.session_scope() as repo:
        if repo.patient("sarah") is None:
            from seed.demo_seed import load
            load(repo)
        recovered = investigation.recover(repo)
        logging.getLogger("surgiguard.recovery").info("Requeued %d persisted investigations", len(recovered))
    scheduler.start()
    import os
    import threading
    if os.getenv("WOUND_MODEL", "on").lower() != "off":
        def _warm():
            try:
                from .integrations import d1_wound
                d1_wound._d1()
                from surgiguard_d1.wound import model as wm
                if wm.available()[0]:
                    wm.load_heads()
                    wm._encoder(wm.load_heads().get("encoder"))
            except Exception:
                logging.getLogger("surgiguard").exception("wound model warm-up failed")
        threading.Thread(target=_warm, daemon=True).start()
    yield
    scheduler.stop()


app = FastAPI(title="SurgiGuard AI backend", version="0.2.0", lifespan=lifespan,
              description="Agentic post-operative surveillance prototype (FICTIONAL data, not a medical device).")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
from .account_scope import guard
app.middleware("http")(guard)
app.mount("/static/photos", StaticFiles(directory=BACKEND_DIR / "seed" / "photos"), name="photos")
(BACKEND_DIR / "uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=BACKEND_DIR / "uploads"), name="uploads")
# Preserve the existing React Native patient UI at /app; expose the teammate's
# patient/family/clinic dashboard at /agent-demo for inspecting the agent workflow.
PATIENT_WEB = BACKEND_DIR.parent / "mobile" / "dist-web"
app.mount("/app", StaticFiles(directory=PATIENT_WEB, html=True, check_dir=False), name="patient-web-preview")
app.mount("/agent-demo", StaticFiles(directory=BACKEND_DIR / "web", html=True), name="agent-dashboard")
app.include_router(d3_demo_router)
app.include_router(d2_router, prefix="/v1")


@app.get("/prototype", include_in_schema=False)
def prototype_page():
    """Story walkthrough across D1 / D2 / D3 on this backend."""
    return FileResponse(BACKEND_DIR / "web" / "prototype.html")


@app.get("/story", include_in_schema=False)
def story_page():
    """The complete story: ESP32 + SurgiGuard API + AI agents on one page."""
    return FileResponse(BACKEND_DIR / "web" / "story.html")


@app.get("/demo", include_in_schema=False)
def d3_demo_page():
    return FileResponse(BACKEND_DIR / "web_demo.html")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/app/")

for r in (account_context, chat, patients, documents, wounds, observations, checkin, investigations, alerts, medications, caregiver,
          demo, integration, hub, motor):
    app.include_router(r.router)


@app.get("/health")
def health():
    from .llm import route
    prov = settings.llm_provider
    return {"status": "ok", "llm": prov, "llm_mode": settings.llm_mode,
            "model": getattr(settings, f"{prov}_model", settings.mistral_model),
            "configured": bool(getattr(settings, f"{prov}_api_key", "")),
            "routes": {a: "/".join(route(a)) for a in ("investigation", "checkin_clarify", "digest", "chat", "protocol")}}
