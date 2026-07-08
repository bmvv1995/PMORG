"""Configurație AI-PM — toate variabilele într-un singur loc.

SPEC §0 + adăugirile din plan. Nicio valoare hardcodată în restul codului.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# --- Odoo (SPEC §0) ---
ODOO_BASE_URL = os.environ.get("ODOO_BASE_URL", "https://horeca.evrika.team")
ODOO_RPC_URL = os.environ.get("ODOO_RPC_URL", "http://127.0.0.1:8069")
ODOO_DB = os.environ.get("ODOO_DB", "horeca")
ODOO_RPC_LOGIN = os.environ.get("ODOO_RPC_LOGIN", "aipm")
ODOO_RPC_PASSWORD = os.environ.get("ODOO_RPC_PASSWORD", "")
ODOO_ADAPTER = os.environ.get("ODOO_ADAPTER", "fake")  # fake | xmlrpc

# --- Baza proprie (SPEC §0) ---
PG_DSN = os.environ.get("PG_DSN", "postgresql://aipm:aipm@127.0.0.1:5432/aipm")

# --- LLM (pattern nous, provider-agnostic) ---
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "").strip()
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-pro")

# --- Embeddings (dim fixă 1024, SPEC §0; provider default: Jina v3) ---
EMBED_API_KEY = os.environ.get("EMBED_API_KEY", "")
EMBED_BASE_URL = os.environ.get("EMBED_BASE_URL", "https://api.jina.ai/v1")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "jina-embeddings-v3")
EMBED_DIM = 1024  # fixat de SPEC §0 — nu e configurabil

# --- Serviciu ---
AIPM_PORT = _int("AIPM_PORT", 8090)
AIPM_BIND = os.environ.get("AIPM_BIND", "127.0.0.1")
AIPM_AUTH_TOKEN = os.environ.get("AIPM_AUTH_TOKEN", "")

# --- Ingest ---
# Bucla de ingest pornește doar dacă e activată EXPLICIT. Instalarea de produs
# (PLAN-INTEGRARE etapa 1) livrează memoria inertă: conducta se deschide prin
# decizie, nu prin default (P4 — poarta înaintea conductei).
INGEST_ENABLED = _bool("INGEST_ENABLED", True)  # true = compat cu deploy-ul existent
CHATTER_POLL_SECONDS = _int("CHATTER_POLL_SECONDS", 60)
INGEST_MAX_ATTEMPTS = _int("INGEST_MAX_ATTEMPTS", 5)
MAX_SOURCE_CHARS = _int("MAX_SOURCE_CHARS", 6000)
EXTRACT_MIN_CONFIDENCE = _float("EXTRACT_MIN_CONFIDENCE", 0.50)
DEDUP_SIM_THRESHOLD = _float("DEDUP_SIM_THRESHOLD", 0.90)

# --- Chitanțe ---
RECEIPT_MODE = os.environ.get("RECEIPT_MODE", "manual")  # manual (Faza 1) | auto (Faza 2+)
RECEIPT_MAX_ATTEMPTS = _int("RECEIPT_MAX_ATTEMPTS", 10)

# --- Recall ---
RECALL_TOP_K = _int("RECALL_TOP_K", 12)
RECALL_MIN_SIM = _float("RECALL_MIN_SIM", 0.60)
RECALL_STRUCT_SLOTS = _int("RECALL_STRUCT_SLOTS", 6)
SESSION_MAX_TURNS = _int("SESSION_MAX_TURNS", 6)

# --- Adaptor ---
RPC_TIMEOUT_SECONDS = _int("RPC_TIMEOUT_SECONDS", 15)

# --- Rapoarte ---
DUE_SOON_DAYS = _int("DUE_SOON_DAYS", 3)
STALE_QUESTION_DAYS = _int("STALE_QUESTION_DAYS", 14)
EXTERNAL_RECURRENCE_MIN = _int("EXTERNAL_RECURRENCE_MIN", 3)
