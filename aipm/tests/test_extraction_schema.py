"""Normalizarea §2 — regulile deterministe din plan A.§2 (FakeLLM, fără rețea)."""

import json
from datetime import datetime

import pytest

from aipm.engine import extraction
from aipm.engine.extraction import ExtractionInvalid, extract

from .helpers import entity, extract_response, make_item

INVENTORY = [
    {"code": c, "label_ro": c, "odoo_model": m, "active": True}
    for c, m in [
        ("PROJECT", "project.project"), ("TASK", "project.task"),
        ("PARTNER", "res.partner"), ("EMPLOYEE", "hr.employee"),
        ("COMPANY", "res.company"),
    ]
]
NOW = datetime(2026, 7, 7, 12, 0)


def _run(fake_llm, *items):
    fake_llm.queue("extract", extract_response(*items))
    return extract("mesaj de test", "Autor", 202, NOW, INVENTORY)


def test_zero_subjects_item_saved_without_subject(fake_llm):
    items = _run(fake_llm, make_item(entities=[entity(role="mentions")]))
    assert len(items) == 1
    assert all(e.role != "subject" for e in items[0].entities)


def test_two_subjects_first_stays_rest_mentions(fake_llm):
    items = _run(fake_llm, make_item(entities=[
        entity(role="subject", mention="unu"),
        entity(role="subject", mention="doi"),
    ]))
    roles = [e.role for e in items[0].entities]
    assert roles == ["subject", "mentions"]


def test_owner_on_non_commitment_demoted(fake_llm):
    items = _run(fake_llm, make_item(kind="decision", entities=[
        entity(role="subject"),
        entity(role="owner", mention="Ion", normalized="Ion Georgescu", hint="PARTNER"),
    ]))
    assert [e.role for e in items[0].entities] == ["subject", "mentions"]


def test_second_owner_demoted(fake_llm):
    items = _run(fake_llm, make_item(kind="commitment", entities=[
        entity(role="subject", hint="TASK"),
        entity(role="owner", mention="Ion", hint="PARTNER"),
        entity(role="owner", mention="Elena", hint="EMPLOYEE"),
    ]))
    assert [e.role for e in items[0].entities] == ["subject", "owner", "mentions"]


def test_invalid_hint_becomes_null(fake_llm):
    items = _run(fake_llm, make_item(entities=[entity(hint="INEXISTENT")]))
    assert items[0].entities[0].anchor_code_hint is None


def test_due_at_ignored_on_non_commitment(fake_llm):
    items = _run(fake_llm, make_item(kind="decision", due_at="2026-08-01"))
    assert items[0].due_at is None


def test_due_at_kept_on_commitment(fake_llm):
    items = _run(fake_llm, make_item(kind="commitment", due_at="2026-08-01"))
    assert str(items[0].due_at) == "2026-08-01"


def test_low_confidence_dropped(fake_llm):
    items = _run(fake_llm, make_item(confidence=0.3), make_item(title="Alta decizie pastrata", confidence=0.8))
    assert len(items) == 1
    assert items[0].title == "Alta decizie pastrata"


def test_invalid_json_repaired_once(fake_llm):
    fake_llm.queue("extract", "NU E JSON", extract_response(make_item()))
    items = extract("mesaj", None, None, NOW, INVENTORY)
    assert len(items) == 1
    assert len(fake_llm.calls) == 2  # apel + reparare


def test_invalid_twice_raises_extraction_invalid(fake_llm):
    fake_llm.queue("extract", "NU E JSON", json.dumps({"items": [{"kind": "gresit"}]}))
    with pytest.raises(ExtractionInvalid):
        extract("mesaj", None, None, NOW, INVENTORY)


def test_unaccent_folds_diacritics():
    assert extraction.unaccent("Amenajare Terasă Vară ș ț â î") == "Amenajare Terasa Vara s t a i"
