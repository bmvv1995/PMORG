"""Etapa 7 din PLAN-INTEGRARE: /api/recall e citire PURĂ.

Spre deosebire de /api/chat (care ingestează întrebarea, cu autor anonim),
/api/recall nu scrie nimic: numărul de rânduri din memorie și din jurnalul
de ingest rămâne neschimbat — condiția ca PM-ul să-și vadă memoria fără să
deschidă pe furiș conducta de scriere (P1/P4).
"""

import json

import pytest
from fastapi.testclient import TestClient

from .helpers import narrate_response

NO_ENTITIES = json.dumps({"entities": []})


@pytest.fixture()
def client(monkeypatch, clean_db, fake_adapter):
    from aipm import config
    from aipm.main import app

    monkeypatch.setattr(config, "AIPM_AUTH_TOKEN", "secret-token")
    return TestClient(app, headers={"Authorization": "Bearer secret-token"})


def _row_counts(db):
    with db.transaction() as conn:
        return {
            "memory_item": conn.execute("SELECT count(*) AS n FROM memory_item").fetchone()["n"],
            "ingest_log": conn.execute("SELECT count(*) AS n FROM ingest_log").fetchone()["n"],
        }


def test_recall_answers_without_writing(client, clean_db, fake_llm, no_embeddings):
    before = _row_counts(clean_db)
    fake_llm.queue("query", NO_ENTITIES)
    fake_llm.queue("narrate", narrate_response("Nu am nimic memorat despre asta."))

    resp = client.post("/api/recall", json={"message": "ce știi despre terasă?"})

    assert resp.status_code == 200
    body = resp.json()
    assert "answer_ro" in body and "session_id" in body
    assert _row_counts(clean_db) == before  # zero scrieri


def test_recall_requires_token(clean_db, fake_adapter, monkeypatch):
    from aipm import config
    from aipm.main import app

    monkeypatch.setattr(config, "AIPM_AUTH_TOKEN", "secret-token")
    assert TestClient(app).post("/api/recall", json={"message": "x"}).status_code == 401


def test_chat_still_ingests_but_recall_does_not(client, clean_db, fake_llm, no_embeddings):
    """Contrastul care ține contractul: /api/chat scrie în ingest_log, /api/recall nu."""
    fake_llm.queue("query", NO_ENTITIES)
    fake_llm.queue("narrate", narrate_response())
    client.post("/api/recall", json={"message": "întrebare read-only"})
    with clean_db.transaction() as conn:
        n = conn.execute("SELECT count(*) AS n FROM ingest_log").fetchone()["n"]
    assert n == 0
