"""Rapoartele — funcții pure, calculate la cerere (plan A.§7).

Structura payload-ului e fixă: items cu memory_id, title, ancore, câmp discriminant.
Formularea textelor din UI = zonă liberă.
"""

from .. import config, db
from ..adapter import get_adapter
from ..adapter.contract import AdapterError


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


def _live_closed_ids(conn, items: list[dict]) -> tuple[set[str], bool]:
    """Felia C (etapa 8, D3, P3-pur): id-urile itemilor al căror subject e închis
    ACUM în Odoo — derivat live la fiecare apel, nu stocat (redeschiderea în Odoo
    reactivează automat). Odoo indisponibil → nu excludem nimic pe orb, raportul
    se declară degradat (P3: degradarea e vizibilă, nu tăcută)."""
    closable = {
        r["code"]: dict(r)
        for r in conn.execute(
            """SELECT code, odoo_model, closed_field, closed_values
               FROM anchor_type WHERE closed_field IS NOT NULL"""
        ).fetchall()
    }
    subject_ref: dict[str, tuple[str, int]] = {}
    wanted: dict[str, set[int]] = {}
    for i in items:
        for a in i["anchors"]:
            if a["role"] == "subject" and a["anchor_code"] in closable:
                subject_ref[i["id"]] = (a["anchor_code"], a["odoo_res_id"])
                wanted.setdefault(a["anchor_code"], set()).add(a["odoo_res_id"])
    if not wanted:
        return set(), False
    adapter = get_adapter()
    closed_refs: set[tuple[str, int]] = set()
    try:
        for code, ids in wanted.items():
            t = closable[code]
            rows = adapter.search_read(
                t["odoo_model"], [("id", "in", sorted(ids))],
                ["id", t["closed_field"]], context={"active_test": False},
            )
            for r in rows:
                if r.get(t["closed_field"]) in t["closed_values"]:
                    closed_refs.add((code, r["id"]))
    except AdapterError:
        return set(), True
    return {mid for mid, ref in subject_ref.items() if ref in closed_refs}, False


def due_soon() -> dict:
    with db.transaction() as conn:
        rows = conn.execute(
            """SELECT id, kind, title, body, due_at, trust, created_at FROM memory_item
               WHERE kind='commitment' AND status='active'
                 AND due_at IS NOT NULL AND due_at <= current_date + %s
               ORDER BY due_at ASC""",
            (config.DUE_SOON_DAYS,),
        ).fetchall()
        items = _items_payload(conn, rows)
        closed_ids, degraded = _live_closed_ids(conn, items)
        return {
            "report": "due_soon",
            "items": [i for i in items if i["id"] not in closed_ids],
            "excluded_closed": len(closed_ids),
            "degraded": degraded,
        }


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
        missing_due = _items_payload(conn, no_due)
        missing_owner = _items_payload(conn, no_owner)
        closed_due, deg1 = _live_closed_ids(conn, missing_due)
        closed_owner, deg2 = _live_closed_ids(conn, missing_owner)
        return {
            "report": "commitments_missing",
            "missing_due": [i for i in missing_due if i["id"] not in closed_due],
            "missing_owner": [i for i in missing_owner if i["id"] not in closed_owner],
            "excluded_closed": len(closed_due | closed_owner),
            "degraded": deg1 or deg2,
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
