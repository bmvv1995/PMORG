"""Pollerul de chatter — plan A.§3.

Seeding la prima pornire (istoricul NU se ingestează), avans de cursor per mesaj,
oprire pe transient sub cap, apoi retry chitanțe (auto) + backfill embeddings.
"""

import logging
import threading
from datetime import datetime

from .. import config, db
from ..adapter import get_adapter
from ..adapter.contract import AdapterError
from ..engine import pipeline, receipts, resolution
from ..engine.receipts import _normalize_chatter_body

logger = logging.getLogger(__name__)


def _chatter_models(conn) -> list[str]:
    return [
        a["odoo_model"] for a in resolution.load_anchor_inventory(conn) if a["has_chatter"]
    ]


def _get_or_seed_cursor(conn, adapter) -> int:
    row = conn.execute(
        "SELECT last_message_id FROM ingest_cursor WHERE source_type='chatter'"
    ).fetchone()
    if row is not None:  # rândul există = seedat (0 e legitim la chatter gol la go-live)
        return row["last_message_id"]
    # Seeding: max mail.message.id la go-live — backfill istoric DOAR manual (plan A.§3)
    latest = adapter.search_read(
        "mail.message", [("message_type", "=", "comment")], ["id"], limit=1, order="id desc"
    )
    seed = latest[0]["id"] if latest else 0
    conn.execute(
        """INSERT INTO ingest_cursor (source_type, last_message_id) VALUES ('chatter', %s)
           ON CONFLICT (source_type) DO UPDATE SET last_message_id = EXCLUDED.last_message_id,
                                                   updated_at = now()""",
        (seed,),
    )
    logger.info("cursor chatter seeded la mail.message id=%s", seed)
    return seed


def _advance_cursor(message_id: int) -> None:
    with db.transaction() as conn:
        conn.execute(
            """UPDATE ingest_cursor SET last_message_id = %s, updated_at = now()
               WHERE source_type='chatter' AND last_message_id < %s""",
            (message_id, message_id),
        )


def run_cycle(lock: threading.Lock) -> dict:
    """Un ciclu complet: poll → pipeline → retry chitanțe → backfill. Serializat prin lock."""
    with lock:
        adapter = get_adapter()
        stats = {"polled": 0, "done": 0, "stopped_on": None, "receipts": 0, "backfilled": 0}
        try:
            with db.transaction() as conn:
                cursor = _get_or_seed_cursor(conn, adapter)
                models = _chatter_models(conn)
            partner_id = adapter.service_partner_id()
            messages = adapter.search_read(
                "mail.message",
                [
                    ("id", ">", cursor),
                    ("message_type", "=", "comment"),
                    ("model", "in", models),
                    ("author_id", "!=", partner_id),  # anti-buclă (I5)
                ],
                ["id", "body", "author_id", "date", "model", "res_id"],
                limit=100,
                order="id asc",
            )
        except AdapterError as e:
            logger.warning("poll chatter eșuat (Odoo indisponibil): %s", e)
            return stats

        for msg in messages:
            stats["polled"] += 1
            text = _normalize_chatter_body(msg.get("body") or "")
            author = msg.get("author_id") or [None, None]
            try:
                msg_date = datetime.strptime(msg["date"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError, KeyError):
                msg_date = datetime.now()
            try:
                pipeline.ingest_message(
                    source_type="chatter",
                    source_ref=f"mail.message:{msg['id']}",
                    text=text,
                    author_name=author[1],
                    author_partner_id=author[0],
                    msg_date=msg_date,
                )
            except pipeline.TransientIngestError:
                stats["stopped_on"] = msg["id"]  # cursorul NU avansează (plan A.§3 pasul 2)
                break
            _advance_cursor(msg["id"])
            stats["done"] += 1

        if config.RECEIPT_MODE == "auto":
            stats["receipts"] = receipts.retry_pending_receipts()
        stats["backfilled"] = pipeline.backfill_embeddings(20)
        return stats


def replay_source(source_ref: str) -> dict:
    """Replay manual (plan A.§3): DOAR mail.message:{id}; re-citește ÎNAINTE de ștergere;
    itemii vechi ai sursei se retractează (determinism)."""
    if not source_ref.startswith("mail.message:"):
        raise ValueError("replay valid doar pentru source_ref de forma mail.message:{id}")
    message_id = int(source_ref.split(":", 1)[1])
    adapter = get_adapter()
    rows = adapter.search_read(
        "mail.message", [("id", "=", message_id)],
        ["id", "body", "author_id", "date", "model", "res_id"], limit=1,
    )
    if not rows:
        raise LookupError(f"mail.message {message_id} nu mai există în Odoo — refuz fără ștergere")
    msg = rows[0]
    with db.transaction() as conn:
        conn.execute(
            "UPDATE memory_item SET status='retracted' WHERE source_ref=%s", (source_ref,)
        )
        conn.execute(
            "DELETE FROM ingest_log WHERE source_type='chatter' AND source_ref=%s", (source_ref,)
        )
    author = msg.get("author_id") or [None, None]
    try:
        msg_date = datetime.strptime(msg["date"], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        msg_date = datetime.now()
    result = pipeline.ingest_message(
        source_type="chatter",
        source_ref=source_ref,
        text=_normalize_chatter_body(msg.get("body") or ""),
        author_name=author[1],
        author_partner_id=author[0],
        msg_date=msg_date,
    )
    return {"status": result.status, "inserted": result.inserted_ids, "detail": result.detail}
