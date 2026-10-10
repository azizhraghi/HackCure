import os
import sys
from datetime import datetime
from pathlib import Path

os.environ["LLM_MODE"] = "stub"
os.environ["SCHEDULER_ENABLED"] = "0"
os.environ["RUN_AGENTS_INLINE"] = "1"
os.environ["DB_URL"] = "sqlite://"
os.environ.pop("MISTRAL_API_KEY", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.main  # noqa: E402,F401  (registers agent jobs)
from app import clock, db  # noqa: E402
from app.config import settings  # noqa: E402

# A fixed afternoon on day 3, after the 14:00 doses.
DEMO_NOW = datetime(2026, 10, 10, 15, 30)


@pytest.fixture
def repo():
    clock.freeze(DEMO_NOW)
    settings.llm_mode = "stub"
    settings.run_agents_inline = True
    db.configure("sqlite://")
    from seed.demo_seed import load
    with db.session_scope() as r:
        load(r)
        yield r
    clock.reset()


@pytest.fixture
def client(repo):
    from app.main import app
    with TestClient(app) as c:
        yield c
