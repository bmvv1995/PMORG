"""Stratul de claims (migrația 0008) sub adaptorul de contract (S3)."""

import types

import pytest

from aipm.mcp_adapter import MemError, MemoryAdapter

C = {"contract": "pmorg-memory/1.0"}


def _adapter(test_dsn, namespace="ns-test", profile="org-min",
             validators=("id:paul",)):
    from aipm import config, db

    config.PG_DSN = test_dsn
    db.close_pool()
    cfg = types.SimpleNamespace(
        pg_dsn=test_dsn,
        profile_id=profile,
        namespace=namespace,
        run_id="test-run",
        instance_uuid="test-uuid",
        validators=set(validators),
    )
    return MemoryAdapter(cfg)


@pytest.fixture()
def adapter(test_dsn):
    a = _adapter(test_dsn)
    with a.db.transaction() as conn:
        conn.execute("TRUNCATE mem_evidence, mem_claim, mem_outcome CASCADE")
    yield a
    a.db.close_pool()


def _capture(a, ext="m-1", author="id:victor", content="text de test"):
    return a.dispatch("memory_capture_evidence", dict(
        C, external_id=ext, source="test", author_ref=author, content=content))


def _propose(a, ev_id, author="id:victor"):
    return a.dispatch("memory_propose_claim", dict(
        C, statement="afirmație", author_ref=author, evidence_ids=[ev_id],
        anchors=[{"anchor_type": "INITIATIVE", "model": "pmorg.initiative",
                  "res_id": 1, "role": "subject"}]))


def test_registry_from_governed_inventory(adapter):
    reg = adapter.dispatch("memory_negotiate_registry",
                           dict(C, profile_id="org-min"))
    assert reg["anchor_types"]["INITIATIVE"] == "pmorg.initiative"
    assert reg["anchor_types"]["IDENTITY"] == "pmorg.identity"
    with pytest.raises(MemError) as exc:
        adapter.dispatch("memory_negotiate_registry",
                         dict(C, profile_id="org-min",
                              expected_fingerprint="deadbeef"))
    assert exc.value.code == "MEM_REGISTRY_MISMATCH"


def test_capture_dedup_replay(adapter):
    first = _capture(adapter)
    again = _capture(adapter)
    assert first["evidence_id"] == again["evidence_id"]
    assert again["replayed"] is True


def test_unknown_anchor_type_fail_closed(adapter):
    ev = _capture(adapter)
    with pytest.raises(MemError) as exc:
        adapter.dispatch("memory_propose_claim", dict(
            C, statement="x", author_ref="id:victor",
            evidence_ids=[ev["evidence_id"]],
            anchors=[{"anchor_type": "LEAVE_REQUEST", "model": "hr.leave",
                      "res_id": 1}]))
    assert exc.value.code == "MEM_ANCHOR_TYPE_UNKNOWN"


def test_validation_rules(adapter):
    ev = _capture(adapter)
    claim = _propose(adapter, ev["evidence_id"])
    report = _capture(adapter, ext="raport-1", author="id:ana",
                      content="raport independent")

    with pytest.raises(MemError) as exc:  # neautorizat
        adapter.dispatch("memory_validate_claim", dict(
            C, claim_id=claim["claim_id"], validator_ref="id:victor",
            supporting_evidence_id=report["evidence_id"]))
    assert exc.value.code == "MEM_NOT_AUTHORIZED"

    with pytest.raises(MemError) as exc:  # dovadă neindependentă
        adapter.dispatch("memory_validate_claim", dict(
            C, claim_id=claim["claim_id"], validator_ref="id:paul",
            supporting_evidence_id=ev["evidence_id"]))
    assert exc.value.code == "MEM_SELF_VALIDATION"

    with pytest.raises(MemError) as exc:  # hash greșit
        adapter.dispatch("memory_validate_claim", dict(
            C, claim_id=claim["claim_id"], validator_ref="id:paul",
            supporting_evidence_id=report["evidence_id"],
            expected_content_hash="deadbeef"))
    assert exc.value.code == "MEM_HASH_MISMATCH"

    done = adapter.dispatch("memory_validate_claim", dict(
        C, claim_id=claim["claim_id"], validator_ref="id:paul",
        supporting_evidence_id=report["evidence_id"],
        expected_content_hash=report["content_hash"]))
    assert done["status"] == "validated"


def test_supersede_and_epistemic_labels(adapter):
    ev = _capture(adapter)
    c1 = _propose(adapter, ev["evidence_id"])
    c2 = _propose(adapter, ev["evidence_id"], author="id:ana")
    adapter.dispatch("memory_supersede", dict(
        C, old_claim_id=c1["claim_id"], new_claim_id=c2["claim_id"],
        reason="corectat"))
    recall = adapter.dispatch("memory_recall", dict(
        C, anchor={"anchor_type": "INITIATIVE", "model": "pmorg.initiative",
                   "res_id": 1}))
    st = {c["id"]: (c["status"], c["epistemic_label"]) for c in recall["claims"]}
    assert st[c1["claim_id"]] == ("superseded", "hypothesis")
    assert st[c2["claim_id"]] == ("candidate", "hypothesis")


def test_namespace_isolation(adapter, test_dsn):
    ev = _capture(adapter)
    _propose(adapter, ev["evidence_id"])
    other = _adapter(test_dsn, namespace="ns-altul")
    recall = other.dispatch("memory_recall", dict(
        C, anchor={"anchor_type": "INITIATIVE", "model": "pmorg.initiative",
                   "res_id": 1}))
    assert recall["claims"] == []
