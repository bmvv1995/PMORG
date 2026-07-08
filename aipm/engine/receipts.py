"""Chitanțele — SPEC §1.8, mecanica din plan A.§3 pasul 7 (I6).

UN singur punct de intrare pentru toate căile (pipeline, retry, buton manual,
confirm din review): post_receipt(memory_id), serializat per memory_id prin
pg_advisory_xact_lock, cu recuperare fetch-and-compare înainte de orice re-post.
"""

import html
import logging
import re

from .. import config, db
from ..adapter import get_adapter
from ..adapter.contract import AdapterError
from .extraction import KIND_RO

logger = logging.getLogger(__name__)


class NoSubjectAnchor(Exception):
    """Item fără ancoră subject rezolvată — chitanța e interzisă (§1.6.4). API: 409."""


class NoChatterTarget(Exception):
    """Nicio ancoră cu has_chatter — fără chitanță, fără retry (plan A.§3 poller)."""


def receipt_body(kind: str, title: str, body: str, trust_label: str, source_type: str) -> str:
    """Formatul EXACT din SPEC §1.8 — testat caracter-cu-caracter."""
    return (
        f"📌 Consemnat ({KIND_RO[kind]}): {title}\n"
        f"{body}\n"
        f"— aipm · încredere: {trust_label} · sursă: {source_type}"
    )


_TAG_RE = re.compile(r"<[^>]+>")


def _normalize_chatter_body(raw_html: str) -> str:
    """strip tags + unescape + colaps spații; <br> devine \\n înainte de strip."""
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.I)
    text = re.sub(r"</p>\s*<p>", "\n", text, flags=re.I)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    return "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())


def _recover_existing_post(adapter, model: str, res_id: int, expected_first_line: str,
                           created_at, claimed_ids: set[int]) -> int | None:
    """Anti-dublă-postare (fetch-and-compare, plan A.§3): match de prefix exact
    pe prima linie normalizată, cu recency bound și excluderea id-urilor revendicate."""
    partner_id = adapter.service_partner_id()
    rows = adapter.search_read(
        "mail.message",
        [
            ("model", "=", model),
            ("res_id", "=", res_id),
            ("author_id", "=", partner_id),
            ("date", ">=", created_at),
        ],
        ["id", "body"],
        limit=80,
        order="id asc",
    )
    expected = " ".join(expected_first_line.split())
    for row in rows:
        if row["id"] in claimed_ids:
            continue
        normalized = _normalize_chatter_body(row["body"] or "")
        first_line = normalized.splitlines()[0] if normalized else ""
        if first_line == expected:
            return row["id"]
    return None


def post_receipt(memory_id: str) -> dict:
    """Postează (sau recuperează) chitanța pentru un item. Idempotent (I6).

    Incrementul receipt_attempts la eșec RPC se face într-o tranzacție SEPARATĂ —
    tranzacția principală face rollback la excepție și l-ar pierde.
    """
    try:
        return _post_receipt_locked(memory_id)
    except AdapterError:
        with db.transaction() as conn:
            conn.execute(
                "UPDATE memory_item SET receipt_attempts = receipt_attempts + 1 WHERE id=%s",
                (memory_id,),
            )
        raise


def _post_receipt_locked(memory_id: str) -> dict:
    adapter = get_adapter()
    with db.transaction() as conn:
        db.advisory_xact_lock(conn, memory_id)  # serializare per memory_id

        existing = conn.execute(
            "SELECT mail_message_id FROM memory_receipt WHERE memory_id=%s", (memory_id,)
        ).fetchone()
        if existing:
            return {"outcome": "already_posted", "mail_message_id": existing["mail_message_id"]}

        item = conn.execute(
            """SELECT id, kind, title, body, source_type, created_at, receipt_attempts
               FROM memory_item WHERE id=%s""",
            (memory_id,),
        ).fetchone()
        if item is None:
            raise ValueError(f"memory_item {memory_id} nu există")

        anchors = conn.execute(
            """SELECT ma.anchor_code, ma.odoo_res_id, ma.role, ma.confidence, ma.needs_review,
                      at.odoo_model, at.has_chatter
               FROM memory_anchor ma JOIN anchor_type at ON at.code = ma.anchor_code
               WHERE ma.memory_id=%s
               ORDER BY ma.confidence DESC""",
            (memory_id,),
        ).fetchall()

        subject = next((a for a in anchors if a["role"] == "subject"), None)
        if subject is None:
            raise NoSubjectAnchor(str(memory_id))  # precondiție (plan A.§3 pasul 7)

        # Ținta: subject cu chatter; altfel primul mentions cu chatter (doar COMPANY în v1);
        # fără nicio țintă → NoChatterTarget (nu intră în retry — condiția EXISTS din poller)
        if subject["has_chatter"]:
            target = subject
        else:
            target = next(
                (a for a in anchors if a["role"] == "mentions" and a["has_chatter"]), None
            )
        if target is None:
            raise NoChatterTarget(str(memory_id))

        trust_label = "de verificat" if subject["needs_review"] else "înaltă"
        body = receipt_body(item["kind"], item["title"], item["body"], trust_label, item["source_type"])
        first_line = body.splitlines()[0]

        claimed = {
            r["mail_message_id"]
            for r in conn.execute("SELECT mail_message_id FROM memory_receipt").fetchall()
        }

        recovered = _recover_existing_post(
            adapter, target["odoo_model"], target["odoo_res_id"],
            first_line, item["created_at"], claimed,
        )
        mail_message_id = recovered if recovered is not None else adapter.message_post(
            target["odoo_model"], target["odoo_res_id"], body
        )

        conn.execute(
            """INSERT INTO memory_receipt (memory_id, anchor_code, odoo_res_id, mail_message_id)
               VALUES (%s,%s,%s,%s)""",
            (memory_id, target["anchor_code"], target["odoo_res_id"], mail_message_id),
        )
        conn.execute("UPDATE memory_item SET trust=1 WHERE id=%s", (memory_id,))
        return {
            "outcome": "recovered" if recovered is not None else "posted",
            "mail_message_id": mail_message_id,
        }


def retry_pending_receipts() -> int:
    """Retry-ul din ciclul de ingest (doar RECEIPT_MODE=auto): trust=0, subject rezolvat,
    sub cap, fără chitanță, cu cel puțin o țintă posibilă cu chatter (plan A.§3 poller)."""
    with db.transaction() as conn:
        rows = conn.execute(
            """SELECT mi.id FROM memory_item mi
               WHERE mi.trust = 0 AND mi.status = 'active'
                 AND mi.receipt_attempts < %s
                 AND NOT EXISTS (SELECT 1 FROM memory_receipt r WHERE r.memory_id = mi.id)
                 AND EXISTS (SELECT 1 FROM memory_anchor s WHERE s.memory_id = mi.id
                             AND s.role = 'subject')
                 AND EXISTS (SELECT 1 FROM memory_anchor a
                             JOIN anchor_type t ON t.code = a.anchor_code
                             WHERE a.memory_id = mi.id
                               AND a.role IN ('subject','mentions') AND t.has_chatter)
               ORDER BY mi.created_at LIMIT 50""",
            (config.RECEIPT_MAX_ATTEMPTS,),
        ).fetchall()
    posted = 0
    for r in rows:
        try:
            post_receipt(str(r["id"]))
            posted += 1
        except (AdapterError, NoChatterTarget, NoSubjectAnchor):
            continue
    return posted
