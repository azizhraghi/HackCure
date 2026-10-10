"""Runs agent jobs off the request thread so API calls (and the urgent path) never wait for an LLM.

Jobs receive ids and open their own DB session. With settings.run_agents_inline (tests) they run synchronously.
"""

import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .config import settings

log = logging.getLogger("surgiguard.runner")
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="agent")
_jobs: dict[str, Callable] = {}


def job(name: str):
    def deco(fn):
        _jobs[name] = fn
        return fn
    return deco


def submit(name: str, *args) -> None:
    if settings.run_agents_inline:
        _call(name, *args)
    else:
        _executor.submit(_call, name, *args)


def _call(name: str, *args) -> None:
    fn = _jobs.get(name)
    if fn is None:
        log.warning("no job registered for %s", name)
        return
    try:
        fn(*args)
    except Exception:  # an agent failure must never break the caller
        log.error("job %s failed:\n%s", name, traceback.format_exc())
