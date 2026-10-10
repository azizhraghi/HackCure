"""SurgiGuard AI backend: FastAPI app, routers and scheduler."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db
from .config import settings
from .agents import investigation  # noqa: F401  (registers the runner job)
from .routers import alerts, chat, investigations, medications, observations, patients

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.engine()
    with db.session_scope() as repo:
        if repo.patient("sarah") is None:
            from seed.demo_seed import load
            load(repo)
    yield


app = FastAPI(title="SurgiGuard AI backend", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static/photos", StaticFiles(directory=SEED_DIR / "photos"), name="photos")
UPLOADS = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")

for r in (chat.router, patients.router, observations.router, alerts.router, medications.router,
          investigations.router):
    app.include_router(r)


@app.get("/health")
def health():
    return {"status": "ok", "llm": "mistral", "llm_mode": settings.llm_mode, "model": settings.mistral_model,
            "configured": bool(settings.mistral_api_key)}
