"""Harness-ul suitei de rezoluție (plan §D) — FakeOdooAdapter + LLM REAL.

Poarta: 100% pe cazurile `must`, ≥85% total. Rulează local cu LLM_API_KEY setat:
    pytest -m llm aipm/tests/test_resolution_suite.py -v
CI-ul implicit îl sare (fără cheie / fără -m llm).
"""

import pathlib

import pytest
import yaml

from aipm import config
from aipm.engine.extraction import EntityMention
from aipm.engine.resolution import resolve_entities

CASES = yaml.safe_load(
    (pathlib.Path(__file__).parent / "resolution_cases" / "cases.yaml").read_text(encoding="utf-8")
)

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(not config.LLM_API_KEY, reason="LLM_API_KEY nu e setat"),
]


def _outcome(resolution) -> tuple[str, str | None, int | None]:
    if resolution.external:
        return ("external", None, None)
    if resolution.anchor is None:
        return ("none", None, None)
    a = resolution.anchor
    return ("review" if a.needs_review else "accept", a.anchor_code, a.odoo_res_id)


def _run_case(clean_db, fake_adapter, case) -> tuple[bool, str]:
    e = case["entity"]
    entity = EntityMention(
        role=e["role"],
        mention_text=e["mention"],
        normalized_text=e["normalized"],
        anchor_code_hint=e["hint"],
    )
    with clean_db.transaction() as conn:
        results = resolve_entities(conn, fake_adapter, [entity], case["kind"])
    outcome, anchor, res_id = _outcome(results[0])
    exp = case["expect"]
    ok = outcome == exp["outcome"]
    if ok and exp["outcome"] in ("accept",):
        ok = anchor == exp["anchor"] and res_id == exp["res_id"]
    if ok and exp["outcome"] == "review" and "anchor" in exp:
        ok = anchor == exp["anchor"]
    return ok, f"{case['id']}: expected {exp}, got ({outcome}, {anchor}, {res_id})"


def test_resolution_suite_gate(clean_db, fake_adapter):
    """Rulează TOATE cazurile și aplică poarta agregat (nu per caz — LLM-ul e stocastic
    pe cazurile should; must-urile însă nu au voie să pice)."""
    must_fail, should_fail, details = [], [], []
    must_total = sum(1 for c in CASES if c["severity"] == "must")
    for case in CASES:
        ok, detail = _run_case(clean_db, fake_adapter, case)
        if not ok:
            details.append(detail)
            (must_fail if case["severity"] == "must" else should_fail).append(case["id"])
    total = len(CASES)
    passed = total - len(must_fail) - len(should_fail)
    print(f"\nSuita de rezoluție: {passed}/{total} "
          f"(must: {must_total - len(must_fail)}/{must_total})")
    for d in details:
        print("  FAIL", d)
    assert not must_fail, f"cazuri MUST picate: {must_fail}"
    assert passed / total >= 0.85, f"rata totală {passed}/{total} sub poarta de 85%"
