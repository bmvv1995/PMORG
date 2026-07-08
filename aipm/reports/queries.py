"""Rapoartele — funcții pure, calculate la cerere (plan A.§7).

Structura payload-ului e fixă: items cu memory_id, title, ancore, câmp discriminant.
Formularea textelor din UI = zonă liberă.
"""

from .. import config, db


def _anchors_for(conn, memory_ids: list[str]) -> dict[str, list[dict]]:
    if not memory_ids:
        return {}
    rows = conn.execute(
        """SELECT ma.memory_id, ma.anchor_code, ma.odoo_res_id, ma.role,
                  ma.confidence, ma.needs_review, at.label_ro, at.odoo_model, at.url_template
           FROM memory_anchor ma JOIN anchor_type at ON at.code = ma.anchor_code
           WHERE ma.memory_id = ANY(%s::uuid[])""",
        (memory_ids,),
    ).fetchall()
    out: dict[str, list[dict]] = {}
    for r in rows:
        d = dict(r)
        d["memory_id"] = str(d["memory_id"])
        d["url"] = r["url_template"].format(
            base_url=config.ODOO_BASE_URL,
            odoo_model=r["odoo_model"],
            odoo_res_id=r["odoo_res_id"],
        )
        del d["url_template"]
        out.setdefault(d["memory_id"], []).append(d)
    return out


def _items_payload(conn, rows) -> list[dict]:
    items = [dict(r) | {"id": str(r["id"])} for r in rows]
    anchors = _anchors_for(conn, [i["id"] for i in items])
    for i in items:
        i["anchors"] = anchors.get(i["id"], [])
        for key in ("created_at", "due_at"):
            if i.get(key) is not None:
                i[key] = str(i[key])
    return items


def due_soon() -> dict:
    with db.transaction() as conn:
        rows = conn.execute(
            """SELECT id, kind, title, body, due_at, trust, created_at FROM memory_item
               WHERE kind='commitment' AND status='active'
                 AND due_at IS NOT NULL AND due_at <= current_date + %s
               ORDER BY due_at ASC""",
            (config.DUE_SOON_DAYS,),
        ).fetchall()
        return {"report": "due_soon", "items": _items_payload(conn, rows)}


def commitments_missing() -> dict:
    with db.transaction() as conn:
        no_due = conn.execute(
            """SELECT id, kind, title, body, due_at, trust, created_at FROM memory_item
               WHERE kind='commitment' AND status='active' AND due_at IS NULL
               ORDER BY created_at DESC"""
        ).fetchall()
        no_owner = conn.execute(
            """SELECT mi.id, mi.kind, mi.title, mi.body, mi.due_at, mi.trust, mi.created_at
               FROM memory_item mi
               WHERE mi.kind='commitment' AND mi.status='active'
                 AND NOT EXISTS (SELECT 1 FROM memory_anchor ma
                                 WHERE ma.memory_id = mi.id AND ma.role='owner')
               ORDER BY mi.created_at DESC"""
        ).fetchall()
        return {
            "report": "commitments_missing",
            "missing_due": _items_payload(conn, no_due),
            "missing_owner": _items_payload(conn, no_owner),
        }


def stale_questions() -> dict:
    with db.transaction() as conn:
        rows = conn.execute(
            """SELECT id, kind, title, body, due_at, trust, created_at FROM memory_item
               WHERE kind='open_question' AND status='active'
                 AND created_at < now() - make_interval(days => %s)
               ORDER BY created_at ASC""",
            (config.STALE_QUESTION_DAYS,),
        ).fetchall()
        return {"report": "stale_questions", "items": _items_payload(conn, rows)}


def external_recurring() -> dict:
    with db.transaction() as conn:
        rows = conn.execute(
            """SELECT m.normalized_text, count(*) AS mentions,
                      array_agg(DISTINCT m.memory_id::text) AS memory_ids
               FROM external_entity_mention m
               LEFT JOIN external_entity_status s ON s.normalized_text = m.normalized_text
               WHERE COALESCE(s.status, 'open') = 'open'
               GROUP BY m.normalized_text
               HAVING count(*) >= %s
               ORDER BY count(*) DESC""",
            (config.EXTERNAL_RECURRENCE_MIN,),
        ).fetchall()
        return {"report": "external_recurring", "items": [dict(r) for r in rows]}


REPORTS = {
    "due_soon": due_soon,
    "commitments_missing": commitments_missing,
    "stale_questions": stale_questions,
    "external_recurring": external_recurring,
}
