"""Pipeline-ul de scriere — plan A.§3, pașii 1–7.

O singură tranzacție PG per mesaj-sursă, savepoint per item, idempotență prin
ingest_log, anti-poison prin attempts, dedup pe două niveluri, chitanță după commit.
"""

import dataclasses
import hashlib
import logging
from datetime import datetime

from .. import config, db
from ..adapter import get_adapter
from . import embeddings, llm, receipts, resolution
from .extraction import ExtractedItem, ExtractionInvalid, extract, unaccent

logger = logging.getLogger(__name__)


class TransientIngestError(Exception):
    """Eroare transientă sub capul de attempts — cursorul NU avansează."""


@dataclasses.dataclass
class IngestResult:
    status: str  # done | extract_failed | no_items | error | skipped
    inserted_ids: list[str] = dataclasses.field(default_factory=list)
    detail: str | None = None


def content_hash(item: ExtractedItem, subject: resolution.ResolvedAnchor | None) -> str:
    subject_part = f"{subject.anchor_code}:{subject.odoo_res_id}" if subject else "nosubject"
    payload = "|".join(
        [item.kind, subject_part, unaccent(item.title).lower(), unaccent(item.body).lower()]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _semantic_duplicate(conn, item_kind: str, subject, embedding) -> str | None:
    """Dedup nivel 2 (plan A.§3): același kind + același subject + 30 zile + activ."""
    if embedding is None or subject is None:
        return None
    row = conn.execute(
        """SELECT mi.id FROM memory_item mi
           JOIN memory_anchor ma ON ma.memory_id = mi.id AND ma.role = 'subject'
           WHERE mi.kind = %s AND mi.status = 'active' AND mi.embedding IS NOT NULL
             AND ma.anchor_code = %s AND ma.odoo_res_id = %s
             AND mi.created_at > now() - interval '30 days'
             AND 1 - (mi.embedding <=> %s::vector) >= %s
           ORDER BY mi.embedding <=> %s::vector LIMIT 1""",
        (
            item_kind,
            subject.anchor_code,
            subject.odoo_res_id,
            embedding,
            config.DEDUP_SIM_THRESHOLD,
            embedding,
        ),
    ).fetchone()
    return str(row["id"]) if row else None


def _upsert_log(conn, source_type, source_ref, status, attempts=0, items_count=0, detail=None):
    conn.execute(
        """INSERT INTO ingest_log (source_type, source_ref, status, attempts, items_count, detail)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (source_type, source_ref)
           DO UPDATE SET status = EXCLUDED.status, attempts = EXCLUDED.attempts,
                         items_count = EXCLUDED.items_count, detail = EXCLUDED.detail,
                         processed_at = now()""",
        (source_type, source_ref, status, attempts, items_count, detail),
    )


def ingest_message(
    source_type: str,
    source_ref: str,
    text: str,
    author_name: str | None,
    author_partner_id: int | None,
    msg_date: datetime,
) -> IngestResult:
    adapter = get_adapter()

    # 1. Idempotență — 'retrying' NU contează ca procesat (plan A.§3 pasul 1)
    with db.transaction() as conn:
        row = conn.execute(
            "SELECT status, attempts FROM ingest_log WHERE source_type=%s AND source_ref=%s",
            (source_type, source_ref),
        ).fetchone()
        attempts = row["attempts"] if row else 0
        if row and row["status"] != "retrying":
            return IngestResult(status="skipped", detail=row["status"])
        inventory = resolution.load_anchor_inventory(conn)

    # 2. Extracție — transient → retrying/attempts; invalid → extract_failed
    try:
        items = extract(text, author_name, author_partner_id, msg_date, inventory)
    except llm.LLMTransientError as e:
        attempts += 1
        with db.transaction() as conn:
            if attempts >= config.INGEST_MAX_ATTEMPTS:
                _upsert_log(conn, source_type, source_ref, "error", attempts, 0, str(e)[:500])
            else:
                _upsert_log(conn, source_type, source_ref, "retrying", attempts, 0, str(e)[:500])
        if attempts >= config.INGEST_MAX_ATTEMPTS:
            return IngestResult(status="error", detail=str(e)[:200])
        raise TransientIngestError(str(e)) from e
    except ExtractionInvalid as e:
        with db.transaction() as conn:
            _upsert_log(conn, source_type, source_ref, "extract_failed", attempts, 0, str(e)[:500])
        return IngestResult(status="extract_failed", detail=str(e)[:200])

    if not items:
        with db.transaction() as conn:
            _upsert_log(conn, source_type, source_ref, "no_items", attempts)
        return IngestResult(status="no_items")

    # 3–6. Rezoluție + embedding + dedup + insert — O tranzacție, savepoint per item
    inserted: list[str] = []
    details: list[str] = []
    with db.transaction() as conn:
        for item in items:
            resolutions = resolution.resolve_entities(
                conn, adapter, item.entities, item.kind, context_text=text
            )
            subject = next(
                (r.anchor for r in resolutions if r.anchor and r.anchor.role == "subject"), None
            )
            for r in resolutions:
                if r.drop_detail:
                    details.append(f"rezolutie_esuata[{r.entity.mention_text}]: {r.drop_detail}")

            try:
                vector = embeddings.embed_one(f"{item.title}\n{item.body}")
            except embeddings.EmbeddingUnavailable as e:
                vector = None
                details.append(f"embedding_indisponibil: {str(e)[:100]}")

            chash = content_hash(item, subject)
            dup = _semantic_duplicate(conn, item.kind, subject, vector)
            if dup:
                details.append(f"dedup_semantic: {dup}")
                continue

            try:
                with db.savepoint(conn):
                    row = conn.execute(
                        """INSERT INTO memory_item
                             (kind, title, body, quote, due_at, source_type, source_ref,
                              author_ref, extract_confidence, content_hash, embedding)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           RETURNING id""",
                        (
                            item.kind, item.title, item.body, item.quote, item.due_at,
                            source_type, source_ref, author_partner_id,
                            item.confidence, chash, vector,
                        ),
                    ).fetchone()
                    memory_id = row["id"]
                    for r in resolutions:
                        if r.anchor:
                            with db.savepoint(conn):
                                conn.execute(
                                    """INSERT INTO memory_anchor
                                         (memory_id, anchor_code, odoo_res_id, role,
                                          confidence, resolved_by, needs_review, mention_text)
                                       VALUES (%s,%s,%s,%s,%s,'auto',%s,%s)""",
                                    (
                                        memory_id, r.anchor.anchor_code, r.anchor.odoo_res_id,
                                        r.anchor.role, r.anchor.confidence,
                                        r.anchor.needs_review, r.anchor.mention_text,
                                    ),
                                )
                        elif r.external:
                            conn.execute(
                                """INSERT INTO external_entity_mention (normalized_text, memory_id)
                                   VALUES (%s, %s)""",
                                (unaccent(r.entity.normalized_text).lower(), memory_id),
                            )
                            conn.execute(
                                """INSERT INTO external_entity_status (normalized_text)
                                   VALUES (%s) ON CONFLICT DO NOTHING""",
                                (unaccent(r.entity.normalized_text).lower(),),
                            )
                    inserted.append(str(memory_id))
            except Exception as e:  # coliziune hash / constrângere trigger — doar itemul cade
                details.append(f"item_aruncat[{item.title[:40]}]: {str(e)[:160]}")

        _upsert_log(
            conn, source_type, source_ref, "done", attempts,
            len(inserted), "; ".join(details)[:1000] or None,
        )

    # 7. Chitanțe — DUPĂ commit, doar în modul auto (Faza 2+; A2)
    if config.RECEIPT_MODE == "auto":
        for memory_id in inserted:
            try:
                receipts.post_receipt(memory_id)
            except receipts.NoSubjectAnchor:
                pass  # trust rămâne 0 (§1.6.4)
            except Exception:
                logger.exception("chitanța a eșuat pentru %s — retry la ciclul următor", memory_id)

    return IngestResult(status="done", inserted_ids=inserted, detail="; ".join(details) or None)


def backfill_embeddings(batch: int = 20) -> int:
    """Backfill pentru rândurile cu embedding NULL + dedup aplicat târziu (plan A.§3)."""
    done = 0
    with db.transaction() as conn:
        rows = conn.execute(
            """SELECT mi.id, mi.kind, mi.title, mi.body,
                      ma.anchor_code, ma.odoo_res_id
               FROM memory_item mi
               LEFT JOIN memory_anchor ma ON ma.memory_id = mi.id AND ma.role = 'subject'
               WHERE mi.embedding IS NULL AND mi.status = 'active'
               ORDER BY mi.created_at LIMIT %s""",
            (batch,),
        ).fetchall()
        for r in rows:
            try:
                vector = embeddings.embed_one(f"{r['title']}\n{r['body']}")
            except embeddings.EmbeddingUnavailable:
                break  # providerul e tot jos; reluăm la ciclul următor
            subject = (
                resolution.ResolvedAnchor("subject", r["anchor_code"], r["odoo_res_id"], 1.0, False, "")
                if r["anchor_code"]
                else None
            )
            dup = _semantic_duplicate(conn, r["kind"], subject, vector)
            if dup and dup != str(r["id"]):
                conn.execute(
                    "UPDATE memory_item SET status='retracted' WHERE id=%s", (r["id"],)
                )
                logger.info("dedup la backfill: %s retractat (duplicat al %s)", r["id"], dup)
            else:
                conn.execute(
                    "UPDATE memory_item SET embedding=%s::vector WHERE id=%s", (vector, r["id"])
                )
            done += 1
    return done
