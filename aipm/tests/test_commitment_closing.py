"""Etapa 8 din PLAN-INTEGRARE (decizia D3) — închiderea angajamentelor.

Felia C: un angajament al cărui subject e închis ACUM în Odoo dispare din
rapoarte — derivat live, nu stocat (redeschiderea îl readuce); Odoo picat →
nimic exclus pe orb, raportul se declară degradat. Felia A: omul marchează
'resolved' (audit: resolved_by/at); itemul iese din rapoarte și recall prin
filtrele status='active'. Nicio marcare automată pe judecata AI.
"""

import pytest
from fastapi.testclient import TestClient

from aipm.adapter.contract import AdapterError
from aipm.reports import queries

from .helpers import insert_anchor, insert_item


def _commitment_on_task(conn, task_id=101, due="current_date"):
    mid = insert_item(conn, kind="commitment", title="Montez mobilierul până vineri",
                      body="corp", due_at="2026-07-09")
    insert_anchor(conn, mid, role="subject", anchor_code="TASK", res_id=task_id)
    return mid


def _task(fake_adapter, task_id):
    return next(t for t in fake_adapter._data["project.task"] if t["id"] == task_id)


def test_open_task_commitment_stays_in_due_soon(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = _commitment_on_task(conn)
    report = queries.due_soon()
    assert [i["id"] for i in report["items"]] == [mid]
    assert report["excluded_closed"] == 0 and report["degraded"] is False


def test_closed_task_commitment_derived_out_live(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = _commitment_on_task(conn)
    _task(fake_adapter, 101)["state"] = "1_done"

    report = queries.due_soon()
    assert report["items"] == [] and report["excluded_closed"] == 1

    # P3-pur: nimic stocat — statusul itemului a rămas 'active',
    # iar redeschiderea taskului în Odoo îl readuce automat în raport
    with clean_db.transaction() as conn:
        status = conn.execute(
            "SELECT status FROM memory_item WHERE id=%s", (mid,)
        ).fetchone()["status"]
    assert status == "active"
    _task(fake_adapter, 101)["state"] = "01_in_progress"
    assert [i["id"] for i in queries.due_soon()["items"]] == [mid]


def test_odoo_down_degrades_visibly_not_silently(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = _commitment_on_task(conn)
    _task(fake_adapter, 101)["state"] = "1_done"
    fake_adapter.fail_next("search_read", AdapterError("Odoo picat"))

    report = queries.due_soon()
    # nu excludem pe orb: itemul rămâne, dar raportul se declară degradat
    assert [i["id"] for i in report["items"]] == [mid]
    assert report["degraded"] is True


def test_commitments_missing_also_filters_closed(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = insert_item(conn, kind="commitment", title="Fără termen", body="corp")
        insert_anchor(conn, mid, role="subject", anchor_code="TASK", res_id=102)
    _task(fake_adapter, 102)["state"] = "1_canceled"
    report = queries.commitments_missing()
    assert report["missing_due"] == [] and report["excluded_closed"] == 1
    _task(fake_adapter, 102)["state"] = "01_in_progress"


@pytest.fixture()
def client(monkeypatch, clean_db, fake_adapter):
    from aipm import config
    from aipm.main import app

    monkeypatch.setattr(config, "AIPM_AUTH_TOKEN", "secret-token")
    return TestClient(app, headers={"Authorization": "Bearer secret-token"})


def test_human_resolve_is_audited_and_final(client, clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = _commitment_on_task(conn)

    resp = client.post(f"/api/memory/{mid}/resolve")
    assert resp.status_code == 200 and resp.json() == {"status": "resolved"}
    with clean_db.transaction() as conn:
        row = conn.execute(
            "SELECT status, resolved_by, resolved_at FROM memory_item WHERE id=%s", (mid,)
        ).fetchone()
    assert row["status"] == "resolved"
    assert row["resolved_by"] == "human" and row["resolved_at"] is not None
    # iese din raport prin filtrul status='active'
    assert queries.due_soon()["items"] == []
    # a doua rezolvare = conflict, nu suprascriere tăcută
    assert client.post(f"/api/memory/{mid}/resolve").status_code == 409


def test_resolve_missing_item_404(client, clean_db, fake_adapter):
    import uuid

    assert client.post(f"/api/memory/{uuid.uuid4()}/resolve").status_code == 404
