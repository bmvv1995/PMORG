"""Pollerul de chatter — seeding, avans de cursor, oprire pe transient, anti-buclă (I5)."""

import threading

from aipm.engine import llm
from aipm.ingest.chatter_poller import run_cycle

from .helpers import entity, extract_response, make_item, rescore_response

LOCK = threading.Lock()


def _cursor(clean_db) -> int:
    with clean_db.transaction() as conn:
        row = conn.execute(
            "SELECT last_message_id FROM ingest_cursor WHERE source_type='chatter'"
        ).fetchone()
    return row["last_message_id"] if row else -1


def test_first_run_seeds_cursor_no_history_ingested(clean_db, fake_adapter, fake_llm, no_embeddings):
    # istoric pre-existent în chatter
    fake_adapter.add_chatter_message("project.task", 101, "mesaj istoric vechi", 202, "Ion")
    stats = run_cycle(LOCK)
    assert stats["polled"] == 0  # seeding la max id — istoricul NU se ingestează
    assert _cursor(clean_db) > 0


def test_new_message_ingested_and_cursor_advances(clean_db, fake_adapter, fake_llm, no_embeddings):
    run_cycle(LOCK)  # seed
    mid = fake_adapter.add_chatter_message(
        "project.task", 101, "Am decis să montăm mobilierul sâmbătă", 202, "Ion Georgescu"
    )
    fake_llm.queue(
        "extract",
        extract_response(make_item(
            title="Montaj stabilit sambata",
            entities=[entity(role="subject", normalized="Montaj mobilier terasă", hint="TASK")],
        )),
    )
    fake_llm.queue("rescore", rescore_response((0, "TASK", 101, 0.95)))
    stats = run_cycle(LOCK)
    assert stats["done"] == 1
    assert _cursor(clean_db) == mid
    with clean_db.transaction() as conn:
        row = conn.execute("SELECT source_ref, source_type FROM memory_item").fetchone()
    assert row["source_ref"] == f"mail.message:{mid}" and row["source_type"] == "chatter"


def test_transient_stops_cursor(clean_db, fake_adapter, fake_llm, no_embeddings):
    run_cycle(LOCK)  # seed
    before = _cursor(clean_db)
    fake_adapter.add_chatter_message("project.task", 101, "mesaj cu ghinion", 202, "Ion")
    fake_llm.queue("extract", llm.LLMTransientError("timeout"))
    stats = run_cycle(LOCK)
    assert stats["stopped_on"] is not None
    assert _cursor(clean_db) == before  # cursorul NU a avansat (plan A.§3 pasul 2)


def test_own_receipts_not_ingested(clean_db, fake_adapter, fake_llm, no_embeddings):
    """I5: mesajele postate de utilizatorul aipm nu intră în pipeline."""
    run_cycle(LOCK)  # seed
    fake_adapter.message_post("project.task", 101, "📌 Consemnat (decizie): X\nY\n— aipm · încredere: înaltă · sursă: chat")
    stats = run_cycle(LOCK)
    assert stats["polled"] == 0  # exclus prin author_id != AIPM_PARTNER_ID
