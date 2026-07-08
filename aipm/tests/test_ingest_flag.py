"""Etapa 1 din PLAN-INTEGRARE: memoria se livrează inertă și își declară starea.

INGEST_ENABLED=false ⇒ lifespan-ul NU pornește bucla de chatter, iar
/api/health raportează ingest_enabled/auth_enabled (starea nu e mascată tăcut).
"""

import asyncio
import contextlib

import pytest
from fastapi.testclient import TestClient


def _drive_lifespan(monkeypatch):
    """Consumă _lifespan cap-coadă și întoarce coroutine-urile lansate cu create_task."""
    import aipm.main as main_mod

    async def _idle_loop():
        await asyncio.Event().wait()  # dublură inertă: nu atinge DB/adaptor

    monkeypatch.setattr(main_mod, "_ingest_loop", _idle_loop)
    created = []
    real_create_task = asyncio.create_task

    async def _run():
        def spy(coro, **kw):
            created.append(coro)
            return real_create_task(coro, **kw)

        monkeypatch.setattr(asyncio, "create_task", spy)
        try:
            gen = main_mod._lifespan(main_mod.app)
            await gen.__anext__()
            with contextlib.suppress(StopAsyncIteration):
                await gen.__anext__()
        finally:
            monkeypatch.setattr(asyncio, "create_task", real_create_task)

    asyncio.run(_run())
    return created


def test_lifespan_skips_ingest_task_when_disabled(monkeypatch, clean_db, fake_adapter):
    from aipm import config

    monkeypatch.setattr(config, "INGEST_ENABLED", False)
    assert _drive_lifespan(monkeypatch) == []


def test_lifespan_starts_ingest_task_when_enabled(monkeypatch, clean_db, fake_adapter):
    from aipm import config

    monkeypatch.setattr(config, "INGEST_ENABLED", True)
    created = _drive_lifespan(monkeypatch)
    assert len(created) == 1


def test_health_reports_ingest_and_auth_state(monkeypatch, clean_db, fake_adapter):
    from aipm import config

    monkeypatch.setattr(config, "INGEST_ENABLED", False)
    monkeypatch.setattr(config, "AIPM_AUTH_TOKEN", "secret-token")
    from aipm.main import app

    resp = TestClient(app).get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ingest_enabled"] is False
    assert body["auth_enabled"] is True


def test_bool_env_parsing(monkeypatch):
    from aipm.config import _bool

    for truthy in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv("X_FLAG", truthy)
        assert _bool("X_FLAG", False) is True
    for falsy in ("0", "false", "no", "off", ""):
        monkeypatch.setenv("X_FLAG", falsy)
        assert _bool("X_FLAG", True) is False
    monkeypatch.delenv("X_FLAG", raising=False)
    assert _bool("X_FLAG", True) is True
    assert _bool("X_FLAG", False) is False
