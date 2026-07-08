"""Recall §4 — post-validarea claims (I2), fuziunea prin cote, ancore șterse."""

import json

from aipm import config
from aipm.engine import recall

from .helpers import insert_anchor, insert_item, narrate_response

NO_ENTITIES = json.dumps({"entities": []})


def _narrate_with_claims(*claims):
    return narrate_response("Răspuns.", list(claims))


def test_fabricated_odoo_value_dropped_claim_removed(clean_db, fake_adapter, fake_llm, no_embeddings):
    fake_llm.queue("query", NO_ENTITIES)
    fake_llm.queue(
        "narrate",
        _narrate_with_claims(
            {
                "text": "Termenul e mâine.",
                "status": "fact",
                "support": [{"type": "odoo", "anchor_code": "TASK", "res_id": 101,
                             "field": "date_deadline", "value": "2099-01-01"}],  # valoare FABRICATĂ
            }
        ),
    )
    result = recall.answer("când e termenul?", None)
    assert result["claims"] == []  # suport invalid → claim eliminat (I2)


def test_valid_odoo_support_becomes_fact(clean_db, fake_adapter, fake_llm, no_embeddings):
    with clean_db.transaction() as conn:
        mid = insert_item(conn, title="Decizie montaj", body="corp", status="active")
        insert_anchor(conn, mid, role="subject", anchor_code="TASK", res_id=101)
    fake_llm.queue("query", json.dumps({"entities": [
        {"mention_text": "montaj", "normalized_text": "Montaj mobilier terasă", "anchor_code_hint": "TASK"}
    ]}))
    from .helpers import rescore_response

    fake_llm.queue("rescore", rescore_response((0, "TASK", 101, 0.95)))
    fake_llm.queue(
        "narrate",
        _narrate_with_claims(
            {
                "text": "Termenul taskului e 11 iulie.",
                "status": "hypothesis",  # naratorul greșește status-ul — codul îl forțează
                "support": [{"type": "odoo", "anchor_code": "TASK", "res_id": 101,
                             "field": "date_deadline", "value": "2026-07-11"}],
            }
        ),
    )
    result = recall.answer("când montăm mobilierul?", None)
    assert len(result["claims"]) == 1
    claim = result["claims"][0]
    assert claim["status"] == "fact"  # ≥1 suport odoo valid → fact, forțat de cod
    assert claim["support"][0]["url"].startswith("https://horeca.evrika.team/odoo/project.task/101")


def test_memory_only_support_forced_hypothesis(clean_db, fake_adapter, fake_llm, fixed_embeddings):
    with clean_db.transaction() as conn:
        vec = fixed_embeddings(["decizia de montaj"])[0]
        mid = insert_item(conn, title="Decizie montaj", body="corp", embedding=vec)
        insert_anchor(conn, mid, role="subject", anchor_code="TASK", res_id=101)
    fake_llm.queue("query", NO_ENTITIES)
    fake_llm.queue(
        "narrate",
        _narrate_with_claims(
            {
                "text": "Parcă s-a decis montajul.",
                "status": "fact",  # naratorul minte — codul retrogradează
                "support": [{"type": "memory", "memory_id": mid, "kind": "decision"}],
            }
        ),
    )
    result = recall.answer("decizia de montaj", None)
    assert len(result["claims"]) == 1
    assert result["claims"][0]["status"] == "hypothesis"


def test_unknown_memory_id_support_dropped(clean_db, fake_adapter, fake_llm, no_embeddings):
    fake_llm.queue("query", NO_ENTITIES)
    fake_llm.queue(
        "narrate",
        _narrate_with_claims(
            {
                "text": "Cineva a promis ceva.",
                "status": "hypothesis",
                "support": [{"type": "memory",
                             "memory_id": "00000000-0000-0000-0000-000000000000", "kind": "decision"}],
            }
        ),
    )
    result = recall.answer("ce promisiuni avem?", None)
    assert result["claims"] == []


def test_deleted_anchor_flagged(clean_db, fake_adapter, fake_llm, no_embeddings):
    with clean_db.transaction() as conn:
        mid = insert_item(conn, title="Decizie pe task șters", body="corp")
        insert_anchor(conn, mid, role="subject", anchor_code="TASK", res_id=9999)  # nu există în fake
    fake_llm.queue("query", json.dumps({"entities": [
        {"mention_text": "montaj", "normalized_text": "Montaj mobilier terasă", "anchor_code_hint": "TASK"}
    ]}))
    from .helpers import rescore_response

    fake_llm.queue("rescore", rescore_response((0, "TASK", 101, 0.95)))
    fake_llm.queue("narrate", narrate_response("Răspuns fără claims."))
    result = recall.answer("montajul?", None)
    assert result["claims"] == []  # doar verificăm că fluxul nu crapă pe ancora ștearsă


def test_quota_fusion_structural_items_survive(clean_db, fake_adapter, fake_llm, fixed_embeddings, monkeypatch):
    """12 semantice + 3 structurale-only → toate 3 structurale prezente (plan §D)."""
    monkeypatch.setattr(config, "RECALL_MIN_SIM", -1.0)  # embeddings hash-based au similarități mici
    captured = {}

    def capture_narrate(system, user):
        captured["user"] = user
        return narrate_response("ok")

    from aipm.engine import llm

    monkeypatch.setattr(llm, "narrate_json", capture_narrate)

    with clean_db.transaction() as conn:
        struct_ids = []
        for i in range(3):
            mid = insert_item(conn, title=f"Structural {i}", body="corp",
                              source_ref=f"chat:t:s{i}", content_hash=f"s{i}")
            insert_anchor(conn, mid, role="subject", anchor_code="PROJECT", res_id=11)
            struct_ids.append(mid)  # FĂRĂ embedding → invizibile semantic
        for i in range(12):
            vec = fixed_embeddings([f"semantic {i}"])[0]
            insert_item(conn, title=f"Semantic {i}", body="corp", embedding=vec,
                        source_ref=f"chat:t:m{i}", content_hash=f"m{i}")

    fake_llm.queue("query", json.dumps({"entities": [
        {"mention_text": "terasa", "normalized_text": "Amenajare Terasă Vară", "anchor_code_hint": "PROJECT"}
    ]}))
    from .helpers import rescore_response

    fake_llm.queue("rescore", rescore_response((0, "PROJECT", 11, 0.95)))
    recall.answer("ce știm despre terasă?", None)

    memory_block = captured["user"].split("[MEMORIE]")[1]
    for i in range(3):
        assert f"Structural {i}" in memory_block  # cotele garantează prezența structuralului
