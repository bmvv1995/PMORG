"""Fixtures de test: DB efemeră migrată prin migrate.py, FakeOdooAdapter, FakeLLM.

Testele validează chiar migrațiile: fiecare sesiune de test primește o bază
proaspătă pe care rulează 0001+0002 (plan §D).
"""

import os
import uuid

import psycopg
import pytest

ADMIN_DSN = os.environ.get("AIPM_TEST_ADMIN_DSN", "postgresql://aipm:aipm@127.0.0.1:5432/aipm")


@pytest.fixture(scope="session")
def test_dsn():
    dbname = f"aipm_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{dbname}"')
    dsn = ADMIN_DSN.rsplit("/", 1)[0] + f"/{dbname}"
    from aipm.migrations.migrate import run

    run(dsn)
    yield dsn
    with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE "{dbname}" WITH (FORCE)')


@pytest.fixture()
def clean_db(test_dsn, monkeypatch):
    """Pool-ul aipm.db pe baza de test, cu tabelele de date golite între teste."""
    from aipm import config, db

    monkeypatch.setattr(config, "PG_DSN", test_dsn)
    db.close_pool()
    with db.transaction() as conn:
        conn.execute(
            "TRUNCATE memory_item, memory_anchor, memory_receipt, ingest_log, "
            "ingest_cursor, external_entity_mention, external_entity_status, "
            "identity_map, project_map, chat_turn, report_sent CASCADE"
        )
    yield db
    db.close_pool()


@pytest.fixture()
def fake_adapter(monkeypatch):
    from aipm import adapter as adapter_pkg
    from aipm.adapter.fake import FakeOdooAdapter

    fake = FakeOdooAdapter()
    adapter_pkg.set_adapter(fake)
    yield fake
    adapter_pkg.set_adapter(None)


class FakeLLM:
    """Răspunsuri scriptate per rol — testele deterministe nu ating rețeaua."""

    def __init__(self):
        self.responses: dict[str, list[str]] = {}
        self.calls: list[tuple[str, str, str]] = []

    def queue(self, role: str, *responses) -> None:
        """Acceptă string-uri (răspunsuri) sau instanțe Exception (aruncate la apel)."""
        self.responses.setdefault(role, []).extend(responses)

    def _pop(self, role: str, system: str, user: str) -> str:
        self.calls.append((role, system, user))
        queue = self.responses.get(role) or []
        if not queue:
            raise AssertionError(f"FakeLLM: niciun răspuns scriptat pentru rolul {role}")
        response = queue.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture()
def fake_llm(monkeypatch):
    from aipm.engine import llm

    fake = FakeLLM()
    monkeypatch.setattr(llm, "extract_json", lambda s, u: fake._pop("extract", s, u))
    monkeypatch.setattr(llm, "query_entities_json", lambda s, u: fake._pop("query", s, u))
    monkeypatch.setattr(llm, "rescore_json", lambda s, u: fake._pop("rescore", s, u))
    monkeypatch.setattr(llm, "narrate_json", lambda s, u: fake._pop("narrate", s, u))
    yield fake


@pytest.fixture()
def no_embeddings(monkeypatch):
    """Simulează outage-ul providerului de embeddings (plan §3 pasul 4)."""
    from aipm.engine import embeddings

    def _raise(texts):
        raise embeddings.EmbeddingUnavailable("test outage")

    monkeypatch.setattr(embeddings, "embed", _raise)
    yield


@pytest.fixture()
def fixed_embeddings(monkeypatch):
    """Embeddings deterministe: vector constant per text (hash-based)."""
    import hashlib

    from aipm import config
    from aipm.engine import embeddings

    def _embed(texts):
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            base = [b / 255.0 for b in h] * (config.EMBED_DIM // len(h) + 1)
            out.append(base[: config.EMBED_DIM])
        return out

    monkeypatch.setattr(embeddings, "embed", _embed)
    yield _embed
