"""Chat-ul propriu ca sursă de ingest (plan A.§3 „Chat propriu").

Doar mesajul utilizatorului intră în pipeline, asincron, după trimiterea
răspunsului. Idempotență: message_uuid generat de CLIENT (I4).
"""

import logging
from datetime import datetime

from ..engine import pipeline

logger = logging.getLogger(__name__)


def ingest_chat_message(session_id: str, message_uuid: str, text: str) -> None:
    source_ref = f"chat:{session_id}:{message_uuid}"
    try:
        pipeline.ingest_message(
            source_type="chat",
            source_ref=source_ref,
            text=text,
            author_name="utilizator",
            author_partner_id=None,
            msg_date=datetime.now(),
        )
    except pipeline.TransientIngestError:
        # remediul pentru chat = retrimiterea mesajului (uuid nou) — plan A.§2
        logger.warning("ingest chat transient pentru %s — utilizatorul poate retrimite", source_ref)
    except Exception:
        logger.exception("ingest chat eșuat pentru %s", source_ref)
