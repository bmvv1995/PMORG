"""Chitanțele §1.8 — format caracter-cu-caracter, țintă, eșec+retry, recuperare, cursă (I6)."""

import threading

import pytest

from aipm.adapter.contract import AdapterUnavailable
from aipm.engine import receipts
from aipm.engine.receipts import (
    NoChatterTarget,
    NoSubjectAnchor,
    post_receipt,
    receipt_body,
    retry_pending_receipts,
)

from .helpers import insert_anchor, insert_item


def test_receipt_format_exact():
    body = receipt_body("decision", "Titlu", "Corpul.", "înaltă", "chat")
    assert body == "📌 Consemnat (decizie): Titlu\nCorpul.\n— aipm · încredere: înaltă · sursă: chat"
    body2 = receipt_body("open_question", "T", "B", "de verificat", "chatter")
    assert body2 == "📌 Consemnat (întrebare deschisă): T\nB\n— aipm · încredere: de verificat · sursă: chatter"


def _item_with_subject(conn, *, anchor_code="TASK", res_id=101, needs_review=False, **kw):
    mid = insert_item(conn, **kw)
    insert_anchor(conn, mid, role="subject", anchor_code=anchor_code, res_id=res_id,
                  needs_review=needs_review)
    return mid


def test_post_receipt_happy_path(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = _item_with_subject(conn, source_ref="chat:a:1")
    result = post_receipt(mid)
    assert result["outcome"] == "posted"
    with clean_db.transaction() as conn:
        item = conn.execute("SELECT trust FROM memory_item WHERE id=%s", (mid,)).fetchone()
        receipt = conn.execute("SELECT * FROM memory_receipt WHERE memory_id=%s", (mid,)).fetchone()
    assert item["trust"] == 1
    assert receipt["anchor_code"] == "TASK" and receipt["odoo_res_id"] == 101
    # chitanța există în chatter-ul fals, escapată ca la real
    msgs = fake_adapter.search_read(
        "mail.message", [("id", "=", receipt["mail_message_id"])], ["body"]
    )
    assert "Consemnat" in msgs[0]["body"]


def test_no_subject_raises(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = insert_item(conn, source_ref="chat:a:2")
    with pytest.raises(NoSubjectAnchor):
        post_receipt(mid)


def test_company_subject_falls_back_to_mentions(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = insert_item(conn, kind="decision", source_ref="chat:a:3")
        insert_anchor(conn, mid, role="subject", anchor_code="COMPANY", res_id=1)
        insert_anchor(conn, mid, role="mentions", anchor_code="PROJECT", res_id=11, confidence=0.9)
    result = post_receipt(mid)
    with clean_db.transaction() as conn:
        receipt = conn.execute("SELECT anchor_code FROM memory_receipt WHERE memory_id=%s", (mid,)).fetchone()
    assert receipt["anchor_code"] == "PROJECT"  # COMPANY nu are chatter (§1.8)


def test_company_without_chatter_mentions_raises(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = insert_item(conn, source_ref="chat:a:4")
        insert_anchor(conn, mid, role="subject", anchor_code="COMPANY", res_id=1)
    with pytest.raises(NoChatterTarget):
        post_receipt(mid)


def test_failure_increments_attempts_then_retry_succeeds(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = _item_with_subject(conn, source_ref="chat:a:5")
    fake_adapter.fail_next("message_post", AdapterUnavailable("Odoo jos"))
    with pytest.raises(AdapterUnavailable):
        post_receipt(mid)
    with clean_db.transaction() as conn:
        item = conn.execute(
            "SELECT trust, receipt_attempts FROM memory_item WHERE id=%s", (mid,)
        ).fetchone()
    assert item["trust"] == 0 and item["receipt_attempts"] == 1

    posted = retry_pending_receipts()  # ciclul următor reușește → trust=1, o singură chitanță
    assert posted == 1
    with clean_db.transaction() as conn:
        item = conn.execute("SELECT trust FROM memory_item WHERE id=%s", (mid,)).fetchone()
        count = conn.execute("SELECT count(*) AS c FROM memory_receipt").fetchone()["c"]
    assert item["trust"] == 1 and count == 1


def test_recovery_adopts_existing_post_without_duplicate(clean_db, fake_adapter):
    """Crash după post reușit dar înainte de insert-ul chitanței → recuperare fetch-and-compare."""
    with clean_db.transaction() as conn:
        mid = _item_with_subject(conn, title="Titlu unic recuperare", source_ref="chat:a:6")
        item = conn.execute("SELECT kind, title, body, source_type FROM memory_item WHERE id=%s", (mid,)).fetchone()
    body = receipt_body(item["kind"], item["title"], item["body"], "înaltă", item["source_type"])
    orphan_id = fake_adapter.message_post("project.task", 101, body)  # postarea „pierdută"

    result = post_receipt(mid)
    assert result == {"outcome": "recovered", "mail_message_id": orphan_id}
    msgs = fake_adapter.search_read(
        "mail.message", [("model", "=", "project.task"), ("res_id", "=", 101)], ["id"]
    )
    assert len(msgs) == 1  # zero postări noi


def test_recovery_skips_claimed_message_ids(clean_db, fake_adapter):
    """Un mail.message deja revendicat de alt item NU poate susține a doua chitanță."""
    with clean_db.transaction() as conn:
        mid1 = _item_with_subject(conn, title="Acelasi titlu", source_ref="chat:a:7")
        mid2 = _item_with_subject(conn, title="Acelasi titlu", body="Corp diferit al doilea",
                                  source_ref="chat:a:8", content_hash="alt-hash")
    post_receipt(mid1)
    result2 = post_receipt(mid2)  # primul mesaj e revendicat → se postează unul NOU
    assert result2["outcome"] == "posted"
    with clean_db.transaction() as conn:
        ids = {
            r["mail_message_id"]
            for r in conn.execute("SELECT mail_message_id FROM memory_receipt").fetchall()
        }
    assert len(ids) == 2


def test_post_receipt_is_idempotent(clean_db, fake_adapter):
    with clean_db.transaction() as conn:
        mid = _item_with_subject(conn, source_ref="chat:a:9")
    first = post_receipt(mid)
    second = post_receipt(mid)
    assert second["outcome"] == "already_posted"
    assert second["mail_message_id"] == first["mail_message_id"]


def test_concurrent_posts_single_receipt(clean_db, fake_adapter):
    """Cursa buton manual + retry (plan §D Faza 2): advisory lock → exact o chitanță."""
    with clean_db.transaction() as conn:
        mid = _item_with_subject(conn, source_ref="chat:a:10")
    results, errors = [], []

    def worker():
        try:
            results.append(post_receipt(mid))
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    outcomes = sorted(r["outcome"] for r in results)
    assert outcomes.count("posted") + outcomes.count("recovered") == 1
    assert outcomes.count("already_posted") == 3
    with clean_db.transaction() as conn:
        assert conn.execute("SELECT count(*) AS c FROM memory_receipt").fetchone()["c"] == 1
    msgs = fake_adapter.search_read(
        "mail.message", [("model", "=", "project.task"), ("res_id", "=", 101)], ["id"]
    )
    assert len(msgs) == 1


def test_retry_excludes_unpostable_items(clean_db, fake_adapter):
    """Item cu subject COMPANY fără mentions cu chatter NU intră în retry (plan A.§3 poller)."""
    with clean_db.transaction() as conn:
        mid = insert_item(conn, source_ref="chat:a:11")
        insert_anchor(conn, mid, role="subject", anchor_code="COMPANY", res_id=1)
    assert retry_pending_receipts() == 0
    with clean_db.transaction() as conn:
        item = conn.execute("SELECT receipt_attempts FROM memory_item WHERE id=%s", (mid,)).fetchone()
    assert item["receipt_attempts"] == 0  # nu s-a încercat nimic — fără buclă infinită
