"""Suita golden de recall (PLAN-INTEGRARE etapa 6) — stratul determinist.

Oglinda suitei de rezoluție, pentru calea de citire: cazuri-etalon din
recall_cases/cases.yaml, rulate pe FakeOdooAdapter + FakeLLM (zero rețea),
cu embeddings căzute (recall structural pur — determinist prin construcție).
Poarta: 100% pe cazurile `must`, ≥85% total. O regresie în filtrarea
selecției (retracted/resolved/scurgeri între ancore) sau în post-validarea
claims face suita roșie.
"""

import json
import pathlib

import pytest
import yaml

from aipm.engine import recall

from .helpers import insert_anchor, insert_item

CASES = yaml.safe_load(
    (pathlib.Path(__file__).parent / "recall_cases" / "cases.yaml").read_text(encoding="utf-8")
)

NO_ENTITIES = json.dumps({"entities": []})


def _seed(conn, items: list[dict]) -> list[str]:
    mids = []
    for i, item in enumerate(items):
        mid = insert_item(
            conn,
            title=item["title"],
            body=item.get("body", "corp"),
            kind=item.get("kind", "decision"),
            status=item.get("status", "active"),
            due_at=item.get("due_at"),
            source_ref=f"chat:suite:{i}",
        )
        for a in item.get("anchors", []):
            insert_anchor(conn, mid, role=a["role"], anchor_code=a["code"], res_id=a["res_id"])
        mids.append(mid)
    return mids


def _queue(fake_llm, case: dict, mids: list[str]) -> None:
    entities = [
        {"mention_text": q["mention"], "normalized_text": q["normalized"],
         "anchor_code_hint": q.get("hint")}
        for q in case.get("query", [])
    ]
    fake_llm.queue("query", json.dumps({"entities": entities}) if entities else NO_ENTITIES)
    if case.get("rescore"):
        fake_llm.queue("rescore", json.dumps({
            "scores": [
                {"entity_index": i, "anchor_code": c, "res_id": r, "score": s}
                for i, c, r, s in case["rescore"]
            ]
        }))
    claims = (case.get("narrate") or {}).get("claims", [])
    for claim in claims:
        for s in claim.get("support", []):
            mid_ref = s.get("memory_id", "")
            if isinstance(mid_ref, str) and mid_ref.startswith("$MID"):
                s["memory_id"] = mids[int(mid_ref[4:])]
    fake_llm.queue("narrate", json.dumps({"answer_ro": "Răspuns de suită.", "claims": claims}))


def _memory_block(fake_llm) -> str:
    """Blocul [MEMORIE] trimis naratorului — selecția reală a recall-ului."""
    for role, _system, user in fake_llm.calls:
        if role == "narrate":
            start = user.find("[MEMORIE]")
            end = user.find("[CONVERSAȚIE]", start)
            if end == -1:
                end = user.find("Întrebarea:", start)
            return user[start:end]
    raise AssertionError("naratorul nu a fost apelat")


def _run_case(clean_db, fake_adapter, fake_llm, case) -> tuple[bool, str]:
    with clean_db.transaction() as conn:
        mids = _seed(conn, case.get("seed", []))
    _queue(fake_llm, case, mids)

    result = recall.answer(case["question"], None)
    block = _memory_block(fake_llm)
    exp = case["expect"]

    for title in exp.get("retrieved", []):
        if title not in block:
            return False, f"lipsește din [MEMORIE]: „{title}”"
    for title in exp.get("not_retrieved", []):
        if title in block:
            return False, f"interzis dar prezent în [MEMORIE]: „{title}”"

    if "claims" in exp:
        if exp["claims"] == "empty":
            if result["claims"]:
                return False, f"claims trebuia gol, are {len(result['claims'])}"
        else:
            got = [c["status"] for c in result["claims"]]
            want = [c["status"] for c in exp["claims"]]
            if got != want:
                return False, f"claims: așteptat {want}, primit {got}"
    return True, "ok"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_recall_case_must(clean_db, fake_adapter, fake_llm, no_embeddings, case):
    """Cazurile must trec 100% — fiecare eșec e vizibil individual."""
    if case["severity"] != "must":
        pytest.skip("negardat individual (intră în poarta agregată)")
    ok, detail = _run_case(clean_db, fake_adapter, fake_llm, case)
    assert ok, f"{case['id']} ({case['about']}): {detail}"


def test_recall_suite_gate(clean_db, fake_adapter, fake_llm, no_embeddings):
    """Poarta agregată: ≥85% din TOATE cazurile (must-urile au poartă separată, 100%)."""
    results = []
    for case in CASES:
        with clean_db.transaction() as conn:
            conn.execute(
                "TRUNCATE memory_item, memory_anchor, external_entity_mention, "
                "external_entity_status, chat_turn CASCADE"
            )
        fake_llm.calls.clear()
        fake_llm.responses.clear()
        ok, detail = _run_case(clean_db, fake_adapter, fake_llm, case)
        results.append((case["id"], ok, detail))
    passed = sum(1 for _, ok, _ in results if ok)
    ratio = passed / len(results)
    failures = [f"{cid}: {d}" for cid, ok, d in results if not ok]
    assert ratio >= 0.85, f"poarta ≥85% picată ({passed}/{len(results)}): {failures}"
