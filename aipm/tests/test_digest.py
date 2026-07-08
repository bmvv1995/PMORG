"""Etapa 9 din PLAN-INTEGRARE — digestul proactiv, determinist și idempotent.

Text RO fără LLM; jurnalul de trimitere (report_sent) garantează că a doua
rulare nu repetă aceleași elemente; termenul schimbat readuce elementul
legitim; degradarea Odoo e declarată în text, nu tăcută.
"""

import pytest
from fastapi.testclient import TestClient

from aipm.adapter.contract import AdapterError
from aipm.reports.digest import build_digest

from .helpers import insert_anchor, insert_item


def _seed_due(conn, title="Montez mobilierul", due="2026-07-09", task=101):
    """Angajament complet (termen + responsabil) — apare doar în due_soon."""
    mid = insert_item(conn, kind="commitment", title=title, body="corp", due_at=due)
    insert_anchor(conn, mid, role="subject", anchor_code="TASK", res_id=task)
    insert_anchor(conn, mid, role="owner", anchor_code="EMPLOYEE", res_id=303)
    return mid


def test_digest_text_deterministic_and_marked(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        _seed_due(conn)
        insert_item(conn, kind="commitment", title="Angajament fără termen", body="corp")

    # itemul complet → 1 element (due_soon); cel gol → 2 (fără termen + fără responsabil)
    first = build_digest(mark=True)
    assert first["new_items"] == 3 and first["degraded"] is False
    assert "Termene apropiate" in first["text"] and "Montez mobilierul" in first["text"]
    assert "Angajamente incomplete" in first["text"]

    second = build_digest(mark=True)
    assert second["new_items"] == 0 and second["text"] == ""  # nimic de retrimis


def test_preview_does_not_consume(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        _seed_due(conn)
    preview = build_digest(mark=False)
    assert preview["new_items"] == 1 and preview["marked"] is False
    assert build_digest(mark=True)["new_items"] == 1  # încă netrimis


def test_changed_due_date_reenters_digest(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = _seed_due(conn, due="2026-07-09")
    assert build_digest(mark=True)["new_items"] == 1
    with clean_db.transaction() as conn:
        conn.execute("UPDATE memory_item SET due_at='2026-07-10' WHERE id=%s", (mid,))
    again = build_digest(mark=True)
    assert again["new_items"] == 1 and "2026-07-10" in again["text"]


def test_degradation_is_declared_in_text(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        _seed_due(conn)
    fake_adapter.fail_next("search_read", AdapterError("Odoo picat"))
    result = build_digest(mark=False)
    assert result["degraded"] is True
    assert "Odoo indisponibil" in result["text"]


def test_digest_endpoint_requires_token(clean_db, fake_adapter, monkeypatch):
    from aipm import config
    from aipm.main import app

    monkeypatch.setattr(config, "AIPM_AUTH_TOKEN", "secret-token")
    assert TestClient(app).post("/api/reports/digest", json={}).status_code == 401
    ok = TestClient(app).post(
        "/api/reports/digest", json={"mark": False},
        headers={"Authorization": "Bearer secret-token"},
    )
    assert ok.status_code == 200 and ok.json()["new_items"] == 0
