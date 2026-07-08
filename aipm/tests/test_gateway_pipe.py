"""Etapele 3+4+5 din PLAN-INTEGRARE — conducta de sedimentare de la gateway.

(3) identitatea vine structural (author_key) și trece prin vamă — autor mapat
fixat fără ghicire; (4) poarta de intimitate, deterministă, rulează înaintea
oricărei persistări și consemnează refuzul FĂRĂ conținut; (5) conducta e
închisă cât INGEST_ENABLED=false și idempotentă la redeliverare.
"""

from fastapi.testclient import TestClient

import pytest

from aipm.engine import privacy
from aipm.ingest.gateway_source import ingest_gateway_message, source_ref_for

from .helpers import extract_response, make_item


# ------------------------------------------------------------ poarta (etapa 4)

def test_fold_and_flexions_deterministic():
    terms = [privacy.fold(t) for t in ("salariu", "concediu medical", "PIN")]
    hit = privacy.blocked_terms("Discutăm mărirea SALARIULUI lui Ion", terms)
    assert hit == ["salariu"]  # flexiune + diacritice + majuscule
    assert privacy.blocked_terms("A cerut concediu  medical de o zi", terms) == []  # spațiu dublu ≠ expresia
    assert privacy.blocked_terms("a cerut concediu medical de o zi", terms) == ["concediu medical"]
    assert privacy.blocked_terms("pinul cardului", terms) == []  # termen scurt: doar exact
    assert privacy.blocked_terms("PIN gresit", terms) == ["pin"]
    # determinism: două rulări, același rezultat
    text = "Salariile și concediu medical, PIN."
    assert privacy.blocked_terms(text, terms) == privacy.blocked_terms(text, terms)


def test_empty_denylist_means_open_gate(tmp_path):
    assert privacy.load_denylist("") == []
    assert privacy.load_denylist(str(tmp_path / "inexistent.txt")) == []
    assert privacy.blocked_terms("orice text", []) == []


def test_denylist_file_parsing(tmp_path):
    f = tmp_path / "deny.txt"
    f.write_text("# comentariu\nSalariu\n\nconcediu medical\n", encoding="utf-8")
    assert privacy.load_denylist(str(f)) == ["salariu", "concediu medical"]


# --------------------------------------------------- conducta (etapele 3+5)

@pytest.fixture()
def denylist(monkeypatch, tmp_path):
    f = tmp_path / "deny.txt"
    f.write_text("salariu\n", encoding="utf-8")
    from aipm import config

    monkeypatch.setattr(config, "PRIVACY_DENYLIST_FILE", str(f))
    return f


def _seed_identity(conn, channel_id="111", partner=202):
    conn.execute(
        """INSERT INTO identity_map
             (channel, channel_id, partner_res_id, display_name, approved_by)
           VALUES ('telegram', %s, %s, 'Ion Georgescu', 'test-migration')""",
        (channel_id, partner),
    )


def test_blocked_message_never_persisted_and_logged_without_content(
    clean_db, fake_adapter, denylist
):
    result = ingest_gateway_message(
        "telegram:111", "Mărim salariul lui Ion la 9000", chat_id="c1", session_id="s1"
    )
    assert result["status"] == "privacy_blocked" and result["terms_blocked"] == 1
    with clean_db.transaction() as conn:
        items = conn.execute("SELECT count(*) AS n FROM memory_item").fetchone()["n"]
        log = conn.execute(
            "SELECT status, detail FROM ingest_log WHERE source_ref=%s",
            (result["source_ref"],),
        ).fetchone()
    assert items == 0
    assert log["status"] == "privacy_blocked"
    assert "salariu" not in (log["detail"] or "")  # refuz consemnat FĂRĂ termeni
    assert "9000" not in (log["detail"] or "")     # ...și fără conținut


def test_clean_message_flows_with_mapped_author(
    clean_db, fake_adapter, fake_llm, fixed_embeddings, denylist
):
    with clean_db.transaction() as conn:
        _seed_identity(conn, "111", 202)
    fake_llm.queue("extract", extract_response(make_item(kind="observation", entities=[])))

    result = ingest_gateway_message(
        "telegram:111", "Îi trimit oferta până vineri", chat_id="c1", session_id="s1"
    )
    assert result["status"] == "done" and len(result["inserted"]) == 1
    with clean_db.transaction() as conn:
        row = conn.execute(
            "SELECT source_type, author_ref FROM memory_item WHERE id=%s",
            (result["inserted"][0],),
        ).fetchone()
    assert row["source_type"] == "gateway"
    assert row["author_ref"] == 202  # vama, nu ghicirea
    assert [c[0] for c in fake_llm.calls] == ["extract"]


def test_redelivery_is_idempotent(clean_db, fake_adapter, fake_llm, fixed_embeddings, denylist):
    fake_llm.queue("extract", extract_response(make_item(kind="observation", entities=[])))
    first = ingest_gateway_message("telegram:9", "Mesaj unic", "c1", "s1")
    second = ingest_gateway_message("telegram:9", "Mesaj unic", "c1", "s1")
    assert first["status"] == "done"
    assert second["status"] == "skipped"  # același source_ref → dedup ingest_log
    assert first["source_ref"] == second["source_ref"] == source_ref_for("c1", "s1", "Mesaj unic")


# ------------------------------------------------------------- endpoint (5)

@pytest.fixture()
def client(monkeypatch, clean_db, fake_adapter):
    from aipm import config
    from aipm.main import app

    monkeypatch.setattr(config, "AIPM_AUTH_TOKEN", "secret-token")
    return TestClient(app, headers={"Authorization": "Bearer secret-token"})


def test_pipe_closed_while_ingest_disabled(client, monkeypatch):
    from aipm import config

    monkeypatch.setattr(config, "INGEST_ENABLED", False)
    resp = client.post("/api/ingest/gateway",
                       json={"author_key": "telegram:1", "text": "orice"})
    assert resp.status_code == 409


def test_endpoint_blocks_synchronously(client, monkeypatch, denylist):
    from aipm import config

    monkeypatch.setattr(config, "INGEST_ENABLED", True)
    resp = client.post("/api/ingest/gateway",
                       json={"author_key": "telegram:1",
                             "text": "salariul lui Ion", "chat_id": "c", "session_id": "s"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "privacy_blocked"


def test_endpoint_accepts_clean_text(client, monkeypatch, denylist, fake_llm):
    from aipm import config

    monkeypatch.setattr(config, "INGEST_ENABLED", True)
    fake_llm.queue("extract", extract_response())  # thread-ul async: zero items
    resp = client.post("/api/ingest/gateway",
                       json={"author_key": "telegram:1",
                             "text": "mesaj curat", "chat_id": "c", "session_id": "s"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
