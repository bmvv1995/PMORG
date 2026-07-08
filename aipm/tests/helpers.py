"""Utilitare comune pentru teste — construirea răspunsurilor FakeLLM și seed direct în DB."""

import json


def extract_response(*items) -> str:
    return json.dumps({"items": list(items)})


def make_item(
    kind="decision",
    title="Decizie de test suficient de lungă",
    body="Corpul deciziei de test, auto-conținut.",
    quote="citat verbatim",
    confidence=0.9,
    due_at=None,
    entities=None,
) -> dict:
    return {
        "kind": kind,
        "title": title,
        "body": body,
        "quote": quote,
        "due_at": due_at,
        "confidence": confidence,
        "entities": entities if entities is not None else [],
    }


def entity(role="subject", mention="terasa", normalized="Amenajare Terasă Vară", hint="PROJECT") -> dict:
    return {
        "role": role,
        "mention_text": mention,
        "normalized_text": normalized,
        "anchor_code_hint": hint,
    }


def rescore_response(*scores) -> str:
    """scores: tupluri (entity_index, anchor_code, res_id, score)."""
    return json.dumps(
        {
            "scores": [
                {"entity_index": i, "anchor_code": c, "res_id": r, "score": s}
                for i, c, r, s in scores
            ]
        }
    )


def narrate_response(answer="Răspuns de test.", claims=None) -> str:
    return json.dumps({"answer_ro": answer, "claims": claims or []})


def insert_item(conn, *, kind="decision", title="Titlu test", body="Corp test",
                trust=0, status="active", source_type="chat", source_ref="chat:t:x",
                due_at=None, embedding=None, content_hash=None, created_at=None) -> str:
    import hashlib

    chash = content_hash or hashlib.sha256(f"{kind}|{title}|{body}".encode()).hexdigest()
    row = conn.execute(
        """INSERT INTO memory_item (kind, title, body, quote, due_at, status, trust,
                                    source_type, source_ref, extract_confidence,
                                    content_hash, embedding, created_at)
           VALUES (%s,%s,%s,'',%s,%s,%s,%s,%s,0.90,%s,%s,COALESCE(%s, now()))
           RETURNING id""",
        (kind, title, body, due_at, status, trust, source_type, source_ref,
         chash, embedding, created_at),
    ).fetchone()
    return str(row["id"])


def insert_anchor(conn, memory_id, *, role="subject", anchor_code="TASK", res_id=101,
                  confidence=0.95, needs_review=False, resolved_by="auto") -> int:
    row = conn.execute(
        """INSERT INTO memory_anchor (memory_id, anchor_code, odoo_res_id, role,
                                      confidence, resolved_by, needs_review)
           VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (memory_id, anchor_code, res_id, role, confidence, resolved_by, needs_review),
    ).fetchone()
    return row["id"]
