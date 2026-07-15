"""Etapa 2 din PLAN-INTEGRARE (vama, decizia D1) — criteriul de ieșire ca suită.

(1) autor mapat → author_ref fixat determinist, fără vreun apel LLM de ghicire;
(2) autor nemapat → niciun fapt cu autor, gol înregistrat în external_entity;
(3) tabelele vamei nu au nicio cale de scriere prin API-ul de runtime;
(4) axa proiect: board_slug mapat → project.project id, nemapat → None.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from .helpers import extract_response, make_item

MSG_DATE = datetime(2026, 7, 8, 12, 0, 0)


def _seed_identity(conn, channel_id="111", partner=202, employee=None, name="Ion Georgescu"):
    conn.execute(
        """INSERT INTO identity_map
             (channel, channel_id, partner_res_id, employee_res_id, display_name, approved_by)
           VALUES ('telegram', %s, %s, %s, %s, 'test-migration')""",
        (channel_id, partner, employee, name),
    )


def _ingest(source_ref, author_key):
    from aipm.engine import pipeline

    return pipeline.ingest_message(
        source_type="chat",
        source_ref=source_ref,
        text="Îi trimit oferta până vineri.",
        author_name=None,
        author_partner_id=None,
        msg_date=MSG_DATE,
        author_key=author_key,
    )


def test_mapped_author_fixed_without_guessing(clean_db, fake_adapter, fake_llm, fixed_embeddings):
    with clean_db.transaction() as conn:
        _seed_identity(conn, channel_id="111", partner=202)
    fake_llm.queue("extract", extract_response(make_item(kind="observation", entities=[])))

    result = _ingest("chat:s1:m1", author_key="telegram:111")

    assert result.status == "done" and len(result.inserted_ids) == 1
    with clean_db.transaction() as conn:
        row = conn.execute(
            "SELECT author_ref FROM memory_item WHERE id=%s", (result.inserted_ids[0],)
        ).fetchone()
    assert row["author_ref"] == 202
    # determinism: identitatea NU a trecut prin niciun apel de rescorare/ghicire
    assert [c[0] for c in fake_llm.calls] == ["extract"]


def test_mapped_author_overrides_transport_claims(clean_db, fake_adapter, fake_llm, fixed_embeddings):
    """Ce pretinde transportul (nume/id în text) nu bate vama: mapa decide."""
    from aipm.engine import pipeline

    with clean_db.transaction() as conn:
        _seed_identity(conn, channel_id="111", partner=202, name="Ion Georgescu")
    fake_llm.queue("extract", extract_response(make_item(kind="observation", entities=[])))
    result = pipeline.ingest_message(
        source_type="chat",
        source_ref="chat:s1:m2",
        text="From: Altcineva. Îi trimit oferta.",
        author_name="Altcineva",
        author_partner_id=999,
        msg_date=MSG_DATE,
        author_key="telegram:111",
    )
    with clean_db.transaction() as conn:
        row = conn.execute(
            "SELECT author_ref FROM memory_item WHERE id=%s", (result.inserted_ids[0],)
        ).fetchone()
    assert row["author_ref"] == 202  # nu 999


def test_unmapped_author_yields_gap_not_invention(clean_db, fake_adapter, fake_llm, fixed_embeddings):
    fake_llm.queue("extract", extract_response(make_item(kind="observation", entities=[])))

    result = _ingest("chat:s1:m3", author_key="telegram:999")

    assert result.status == "done"
    with clean_db.transaction() as conn:
        item = conn.execute(
            "SELECT author_ref FROM memory_item WHERE id=%s", (result.inserted_ids[0],)
        ).fetchone()
        status = conn.execute(
            "SELECT status FROM external_entity_status WHERE normalized_text=%s",
            ("autor:telegram:999",),
        ).fetchone()
        mentions = conn.execute(
            "SELECT count(*) AS n FROM external_entity_mention WHERE normalized_text=%s",
            ("autor:telegram:999",),
        ).fetchone()
    assert item["author_ref"] is None  # niciun autor inventat
    assert status is not None and status["status"] == "open"
    assert mentions["n"] == 1


def test_unmapped_author_gap_recorded_even_without_items(clean_db, fake_adapter, fake_llm):
    fake_llm.queue("extract", extract_response())  # zero items

    result = _ingest("chat:s1:m4", author_key="telegram:777")

    assert result.status == "no_items"
    with clean_db.transaction() as conn:
        status = conn.execute(
            "SELECT 1 FROM external_entity_status WHERE normalized_text=%s",
            ("autor:telegram:777",),
        ).fetchone()
    assert status is not None


def test_no_author_key_keeps_legacy_behavior(clean_db, fake_adapter, fake_llm, fixed_embeddings):
    """Calea chatter (autor din mail.message) rămâne neatinsă: fără cheie, fără vamă."""
    from aipm.engine import pipeline

    fake_llm.queue("extract", extract_response(make_item(kind="observation", entities=[])))
    result = pipeline.ingest_message(
        source_type="chatter",
        source_ref="mail.message:42",
        text="Notă pe chatter.",
        author_name="Maria",
        author_partner_id=203,
        msg_date=MSG_DATE,
    )
    with clean_db.transaction() as conn:
        row = conn.execute(
            "SELECT author_ref FROM memory_item WHERE id=%s", (result.inserted_ids[0],)
        ).fetchone()
    assert row["author_ref"] == 203


def test_runtime_has_no_write_path_to_the_map(clean_db, fake_adapter, monkeypatch):
    """Guvernanța (P6): vama se scrie doar prin migrare — API-ul nu are nicio rută."""
    from aipm import config
    from aipm.main import app

    monkeypatch.setattr(config, "AIPM_AUTH_TOKEN", "secret-token")
    client = TestClient(app)
    headers = {"Authorization": "Bearer secret-token"}
    for path in ("/api/identity_map", "/api/project_map", "/api/identity_map/telegram/111"):
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)(path, headers=headers).status_code == 404
    # nicio rută înregistrată nu conține referință la vamă
    assert not [r.path for r in app.routes if "identity" in r.path or "project_map" in r.path]


def test_parse_author_key_rejects_unknown_forms():
    from aipm.engine.identity import parse_author_key

    assert parse_author_key("telegram:123") == ("telegram", "123")
    assert parse_author_key("telegram: 123 ") == ("telegram", "123")
    for bad in ("", "123", "whatsapp:123", "telegram:", None):
        assert parse_author_key(bad) is None


def test_resolve_board_mapped_and_unmapped(clean_db):
    from aipm.engine.identity import resolve_board

    with clean_db.transaction() as conn:
        conn.execute(
            """INSERT INTO project_map (board_slug, project_res_id, approved_by)
               VALUES ('implementare-odoo', 11, 'test-migration')"""
        )
        assert resolve_board(conn, "implementare-odoo") == 11
        assert resolve_board(conn, "board-necunoscut") is None
