"""Etapa 10 din PLAN-INTEGRARE: jurnalul conversației (latura de asistent).

Fiecare răspuns al memoriei se jurnalizează în chat_turn — append-only, în
carantină (nu e memorie, nu susține claims). „Ce a răspuns memoria săptămâna
asta?" are răspuns dintr-o interogare și supraviețuiește restartului (e în PG,
nu în deque-ul de proces). Latura de utilizator NU se jurnalizează încă —
așteaptă poarta de intimitate (etapa 4, P4).
"""

import json

import psycopg
import pytest

from aipm.engine import recall

from .helpers import narrate_response

NO_ENTITIES = json.dumps({"entities": []})


def _ask(fake_llm, question="ce știi despre terasă?", answer="Nimic memorat."):
    fake_llm.queue("query", NO_ENTITIES)
    fake_llm.queue("narrate", narrate_response(answer))
    return recall.answer(question, None)


def test_assistant_turn_journaled(clean_db, fake_adapter, fake_llm, no_embeddings):
    result = _ask(fake_llm, answer="Răspunsul de jurnalizat.")
    with clean_db.transaction() as conn:
        rows = conn.execute(
            "SELECT session_id, role, body, degraded FROM chat_turn ORDER BY id"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["role"] == "assistant"
    assert rows[0]["body"] == "Răspunsul de jurnalizat."
    assert rows[0]["session_id"] == result["session_id"]


def test_user_side_not_journaled_yet(clean_db, fake_adapter, fake_llm, no_embeddings):
    """P4: cuvintele omului nu intră în jurnal înaintea porții de intimitate."""
    _ask(fake_llm, question="întrebare cu conținut personal")
    with clean_db.transaction() as conn:
        n = conn.execute("SELECT count(*) AS n FROM chat_turn WHERE role='user'").fetchone()["n"]
    assert n == 0


def test_weekly_audit_query_answers(clean_db, fake_adapter, fake_llm, no_embeddings):
    for i in range(3):
        _ask(fake_llm, answer=f"Răspuns {i}.")
    with clean_db.transaction() as conn:
        rows = conn.execute(
            """SELECT body FROM chat_turn
               WHERE role='assistant' AND created_at > now() - interval '7 days'
               ORDER BY id"""
        ).fetchall()
    assert [r["body"] for r in rows] == ["Răspuns 0.", "Răspuns 1.", "Răspuns 2."]


def test_journal_is_append_only(clean_db, fake_adapter, fake_llm, no_embeddings):
    _ask(fake_llm)
    with pytest.raises(psycopg.errors.RaiseException):
        with clean_db.transaction() as conn:
            conn.execute("UPDATE chat_turn SET body='rescris'")
    with pytest.raises(psycopg.errors.RaiseException):
        with clean_db.transaction() as conn:
            conn.execute("DELETE FROM chat_turn")


def test_journal_failure_does_not_break_answer(clean_db, fake_adapter, fake_llm,
                                               no_embeddings, monkeypatch):
    """Jurnalul e audit, nu poartă: dacă scrierea lui pică, răspunsul tot pleacă."""
    fake_llm.queue("query", NO_ENTITIES)
    fake_llm.queue("narrate", narrate_response("Răspuns robust."))

    real_transaction = recall.db.transaction
    calls = {"n": 0}

    def flaky_transaction():
        calls["n"] += 1
        if calls["n"] >= 2:  # prima tranzacție = citirea; a doua = jurnalul
            raise RuntimeError("jurnal indisponibil")
        return real_transaction()

    monkeypatch.setattr(recall.db, "transaction", flaky_transaction)
    result = recall.answer("întrebare", None)
    assert result["answer_ro"] == "Răspuns robust."
