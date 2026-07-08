"""Acces PostgreSQL — pool sincron, tranzacții, savepoint, advisory lock.

Stack-ul pipeline e sincron (decizie plan §7); FastAPI îl rulează în threadpool.
"""

import contextlib
import logging
import uuid

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


def _configure(conn: psycopg.Connection) -> None:
    register_vector(conn)
    conn.row_factory = dict_row


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            config.PG_DSN, min_size=1, max_size=8, configure=_configure, open=True
        )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextlib.contextmanager
def transaction():
    """O conexiune cu tranzacție: commit la ieșire normală, rollback la excepție."""
    with get_pool().connection() as conn:
        with conn.transaction():
            yield conn


@contextlib.contextmanager
def savepoint(conn: psycopg.Connection):
    """Savepoint per item (plan §3 pasul 6): itemul căzut se aruncă, restul se comite."""
    with conn.transaction():
        yield


def advisory_xact_lock(conn: psycopg.Connection, memory_id: uuid.UUID | str) -> None:
    """Serializare per memory_id pentru chitanțe (I6). Ține lock-ul până la commit."""
    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 0))", (str(memory_id),)
    )
