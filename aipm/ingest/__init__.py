"""Ingest — sursele de mesaje (chatter Odoo + chat propriu).

ingest_lock serializează ciclul pollerului cu /api/ingest/run și /api/ingest/replay (plan §7).
"""

import threading

ingest_lock = threading.Lock()
