"""Conducta de sedimentare de la gateway — PLAN-INTEGRARE etapele 3+5.

Sursa: hook-ul stock `agent:start` al gateway-ului Hermes (aipm-sediment),
care livrează identitatea REALĂ a expeditorului (user_id după allowlist) ca
author_key + textul mesajului. Ordinea impusă de P4: poarta de intimitate
rulează ÎNAINTE de orice persistare; identitatea trece prin vamă (etapa 2)
în pipeline. Idempotență: source_ref derivat din (chat, sesiune, text) —
redeliverarea aceluiași eveniment e sărită de ingest_log.
"""

import hashlib
import logging
from datetime import datetime

from .. import db
from ..engine import pipeline, privacy

logger = logging.getLogger(__name__)


def source_ref_for(chat_id: str, session_id: str, text: str) -> str:
    digest = hashlib.sha256(f"{session_id}|{text}".encode("utf-8")).hexdigest()[:16]
    return f"gw:{chat_id or 'nochat'}:{digest}"


def ingest_gateway_message(
    author_key: str,
    text: str,
    chat_id: str = "",
    session_id: str = "",
    msg_date: datetime | None = None,
) -> dict:
    source_ref = source_ref_for(chat_id, session_id, text)

    # Poarta ÎNAINTEA conductei (P4): refuzul se consemnează fără conținut.
    hits = privacy.blocked_terms(text)
    if hits:
        with db.transaction() as conn:
            pipeline._upsert_log(
                conn, "gateway", source_ref, "privacy_blocked",
                items_count=0, detail=f"termeni_blocati: {len(hits)}",
            )
        logger.info("mesaj blocat de poarta de intimitate (%s, %d termeni)",
                    source_ref, len(hits))
        return {"status": "privacy_blocked", "terms_blocked": len(hits),
                "source_ref": source_ref}

    result = pipeline.ingest_message(
        source_type="gateway",
        source_ref=source_ref,
        text=text,
        author_name=None,
        author_partner_id=None,
        msg_date=msg_date or datetime.now(),
        author_key=author_key,
    )
    return {"status": result.status, "inserted": result.inserted_ids,
            "source_ref": source_ref}


def ingest_gateway_async(author_key: str, text: str, chat_id: str, session_id: str) -> None:
    """Corpul thread-ului de după accept: transient = redelivery/replay, nu cursor."""
    try:
        ingest_gateway_message(author_key, text, chat_id, session_id)
    except pipeline.TransientIngestError:
        logger.warning("ingest gateway transient — hook-ul poate relivra (idempotent)")
    except Exception:
        logger.exception("ingest gateway eșuat")
