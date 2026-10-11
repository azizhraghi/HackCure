"""Runs agent jobs off the request thread so API calls (and the urgent path) never wait for an LLM.

Jobs receive ids and open their own DB session. With settings.run_agents_inline (tests) they run synchronously.
"""

import logging
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .config import settings

log = logging.getLogger("surgiguard.runner")
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="agent")
_jobs: dict[str, Callable] = {}
_active: set[tuple] = set()
_active_lock = threading.Lock()


def job(name: str):
    def deco(fn):
        _jobs[name] = fn
        return fn
    return deco


def is_pending(name: str, *args) -> bool:
    with _active_lock:
        return (name, *args) in _active


def submit(name: str, *args) -> bool:
    """Coalesce identical queued/running jobs within this server process."""
    key = (name, *args)
    with _active_lock:
        if key in _active:
            return False
        _active.add(key)

    def invoke():
        try:
            _call(name, *args)
        finally:
            with _active_lock:
                _active.discard(key)

    try:
        if settings.run_agents_inline:
            invoke()
        else:
            _executor.submit(invoke)
    except BaseException:
        with _active_lock:
            _active.discard(key)
        raise
    return True


def _call(name: str, *args) -> None:
    fn = _jobs.get(name)
    if fn is None:
        log.warning("no job registered for %s", name)
        return
    try:
        fn(*args)
    except Exception:  # an agent failure must never break the caller
        log.error("job %s failed:\n%s", name, traceback.format_exc())
