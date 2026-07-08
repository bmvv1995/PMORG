"""Idempotență + anti-poison + dedup + constrângeri de rol (I3/I4, plan §D)."""

from datetime import datetime

import pytest

from aipm import config
from aipm.engine import llm, pipeline
from aipm.engine.pipeline import TransientIngestError, ingest_message

from .helpers import entity, extract_response, make_item, rescore_response

NOW = datetime(2026, 7, 7, 12, 0)


def _queue_simple_item(fake_llm, title="Decizie montaj mobilier terasa"):
    fake_llm.queue(
        "extract",
        extract_response(
            make_item(
                title=title,
                entities=[entity(role="subject", mention="montaj", normalized="Montaj mobilier terasă", hint="TASK")],
            )
        ),
    )
    fake_llm.queue("rescore", rescore_response((0, "TASK", 101, 0.95)))


def test_same_source_ref_twice_one_item(clean_db, fake_adapter, fake_llm, no_embeddings):
    _queue_simple_item(fake_llm)
    r1 = ingest_message("chat", "chat:s1:m1", "montăm mobilierul pe terasă", "u", None, NOW)
    assert r1.status == "done" and len(r1.inserted_ids) == 1

    r2 = ingest_message("chat", "chat:s1:m1", "montăm mobilierul pe terasă", "u", None, NOW)
    assert r2.status == "skipped"  # zero apeluri LLM noi — nimic scriptat nu a fost consumat

    with clean_db.transaction() as conn:
        count = conn.execute("SELECT count(*) AS c FROM memory_item").fetchone()["c"]
    assert count == 1


def test_exact_dedup_same_content_different_source(clean_db, fake_adapter, fake_llm, no_embeddings):
    _queue_simple_item(fake_llm)
    ingest_message("chat", "chat:s1:m1", "text", "u", None, NOW)
    _queue_simple_item(fake_llm)  # același title/body/subject → același content_hash
    r2 = ingest_message("chat", "chat:s1:m2", "text", "u", None, NOW)
    assert r2.status == "done" and r2.inserted_ids == []
    assert "item_aruncat" in (r2.detail or "")
    with clean_db.transaction() as conn:
        assert conn.execute("SELECT count(*) AS c FROM memory_item").fetchone()["c"] == 1


def test_poison_message_error_after_cap(clean_db, fake_adapter, fake_llm, no_embeddings, monkeypatch):
    monkeypatch.setattr(config, "INGEST_MAX_ATTEMPTS", 3)
    for _ in range(2):
        fake_llm.queue("extract", llm.LLMTransientError("timeout simulat"))
        with pytest.raises(TransientIngestError):
            ingest_message("chatter", "mail.message:77", "text", "u", 202, NOW)
    with clean_db.transaction() as conn:
        row = conn.execute(
            "SELECT status, attempts FROM ingest_log WHERE source_ref='mail.message:77'"
        ).fetchone()
    assert row["status"] == "retrying" and row["attempts"] == 2

    fake_llm.queue("extract", llm.LLMTransientError("timeout simulat"))
    result = ingest_message("chatter", "mail.message:77", "text", "u", 202, NOW)
    assert result.status == "error"  # cap atins → cursorul poate avansa
    with clean_db.transaction() as conn:
        row = conn.execute(
            "SELECT status, attempts FROM ingest_log WHERE source_ref='mail.message:77'"
        ).fetchone()
    assert row["status"] == "error" and row["attempts"] == 3


def test_owner_type_enforced_by_trigger(clean_db, fake_adapter, fake_llm, no_embeddings):
    # owner cu hint TASK: rezoluția restrânge la {PARTNER, EMPLOYEE} (§1.4) — hint ignorat
    fake_llm.queue(
        "extract",
        extract_response(
            make_item(
                kind="commitment",
                title="Ion se ocupa de montaj pana vineri",
                entities=[
                    entity(role="subject", mention="montaj", normalized="Montaj mobilier terasă", hint="TASK"),
                    entity(role="owner", mention="Ion", normalized="Ion Georgescu", hint="TASK"),
                ],
            )
        ),
    )
    fake_llm.queue("rescore", rescore_response((0, "TASK", 101, 0.95), (1, "PARTNER", 202, 0.95)))
    r = ingest_message("chat", "chat:s1:own1", "text", "u", None, NOW)
    assert len(r.inserted_ids) == 1
    with clean_db.transaction() as conn:
        anchors = conn.execute(
            "SELECT anchor_code, role FROM memory_anchor WHERE memory_id=%s ORDER BY role",
            (r.inserted_ids[0],),
        ).fetchall()
    assert {(a["role"], a["anchor_code"]) for a in anchors} == {("subject", "TASK"), ("owner", "PARTNER")}

    # insert direct cu owner de tip TASK → trigger-ul §1.4 respinge
    from .helpers import insert_anchor, insert_item

    with clean_db.transaction() as conn:
        mid = insert_item(conn, kind="commitment", title="alt", body="alt", source_ref="chat:x:y")
    import psycopg

    with pytest.raises(psycopg.errors.RaiseException):
        with clean_db.transaction() as conn:
            insert_anchor(conn, mid, role="owner", anchor_code="TASK", res_id=101)


def test_kind_subject_matrix_enforced(clean_db, fake_adapter):
    from .helpers import insert_anchor, insert_item
    import psycopg

    with clean_db.transaction() as conn:
        mid = insert_item(conn, kind="rule_candidate", title="regula", body="regula")
    with pytest.raises(psycopg.errors.RaiseException):
        with clean_db.transaction() as conn:
            insert_anchor(conn, mid, role="subject", anchor_code="TASK", res_id=101)  # nu e în §1.5


def test_zero_candidates_becomes_external(clean_db, fake_adapter, fake_llm, no_embeddings):
    fake_llm.queue(
        "extract",
        extract_response(
            make_item(
                kind="observation",
                title="Primaria intarzie avizul de terasa",
                entities=[
                    entity(role="subject", mention="terasa", normalized="Amenajare Terasă Vară", hint="PROJECT"),
                    entity(role="mentions", mention="primăria", normalized="Primăria Chișinău", hint=None),
                ],
            )
        ),
    )
    # doar entitatea cu candidați intră la rescorare (index 0 = proiectul)
    fake_llm.queue("rescore", rescore_response((0, "PROJECT", 11, 0.92)))
    r = ingest_message("chat", "chat:s1:ext1", "text", "u", None, NOW)
    assert len(r.inserted_ids) == 1
    with clean_db.transaction() as conn:
        ext = conn.execute("SELECT normalized_text FROM external_entity_mention").fetchall()
    assert [e["normalized_text"] for e in ext] == ["primaria chisinau"]


def test_low_score_with_candidates_not_external(clean_db, fake_adapter, fake_llm, no_embeddings):
    fake_llm.queue(
        "extract",
        extract_response(
            make_item(
                entities=[
                    entity(role="subject", mention="terasa", normalized="Terasă", hint="PROJECT"),
                    entity(role="mentions", mention="Ion", normalized="Ion", hint="PARTNER"),
                ]
            )
        ),
    )
    fake_llm.queue("rescore", rescore_response((0, "PROJECT", 11, 0.90), (1, "PARTNER", 202, 0.10)))
    r = ingest_message("chat", "chat:s1:low1", "text", "u", None, NOW)
    assert "sub_prag" in (r.detail or "")
    with clean_db.transaction() as conn:
        # candidați EXISTĂ dar scor sub prag → nici ancoră, nici externă (plan A.§3 pasul 6)
        assert conn.execute("SELECT count(*) AS c FROM external_entity_mention").fetchone()["c"] == 0
        anchors = conn.execute(
            "SELECT role FROM memory_anchor WHERE memory_id=%s", (r.inserted_ids[0],)
        ).fetchall()
    assert [a["role"] for a in anchors] == ["subject"]


def test_needs_review_band(clean_db, fake_adapter, fake_llm, no_embeddings):
    # PROJECT: accept 0.85 / review 0.50 → scor 0.70 = ancoră cu needs_review (I3 respectat)
    fake_llm.queue(
        "extract",
        extract_response(make_item(entities=[entity(role="subject", hint="PROJECT")])),
    )
    fake_llm.queue("rescore", rescore_response((0, "PROJECT", 11, 0.70)))
    r = ingest_message("chat", "chat:s1:rev1", "text", "u", None, NOW)
    with clean_db.transaction() as conn:
        a = conn.execute(
            "SELECT needs_review, confidence FROM memory_anchor WHERE memory_id=%s",
            (r.inserted_ids[0],),
        ).fetchone()
    assert a["needs_review"] is True and float(a["confidence"]) == 0.70
