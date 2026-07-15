"""Digestul proactiv — PLAN-INTEGRARE etapa 9 (INTENT fluxul 3).

Text DETERMINIST în română, fără LLM (P1: niciun text proactiv autorat de
model): reutilizează rapoartele existente și jurnalul de trimitere
(report_sent) ca aceleași restanțe să nu fie retrimise zilnic. Ceasul și
transportul rămân ale lui Hermes — aipm doar produce textul.
"""

from .. import db
from . import queries


def _due_soon_lines(report):
    for i in report["items"]:
        key = f"{i['id']}:{i['due_at']}"  # termen schimbat → element nou, legitim
        yield key, f"• (până {i['due_at']}) {i['title']}"


def _missing_lines(report):
    for i in report["missing_due"]:
        yield f"{i['id']}:due", f"• (fără termen) {i['title']}"
    for i in report["missing_owner"]:
        yield f"{i['id']}:owner", f"• (fără responsabil) {i['title']}"


def _stale_lines(report):
    for i in report["items"]:
        yield i["id"], f"• (din {i['created_at'][:10]}) {i['title']}"


def _external_lines(report):
    for i in report["items"]:
        yield i["normalized_text"], f"• „{i['normalized_text']}” — {i['mentions']} mențiuni"


_SECTIONS = (
    ("due_soon", "Termene apropiate sau depășite", queries.due_soon, _due_soon_lines),
    ("commitments_missing", "Angajamente incomplete", queries.commitments_missing, _missing_lines),
    ("stale_questions", "Întrebări rămase deschise", queries.stale_questions, _stale_lines),
    ("external_recurring", "Entități necunoscute recurente", queries.external_recurring, _external_lines),
)


def build_digest(mark: bool = True) -> dict:
    """Construiește digestul din elementele NEtrimise; mark=True le consemnează.

    mark=False = previzualizare pură (nu consumă nimic)."""
    degraded = False
    blocks: list[str] = []
    to_mark: list[tuple[str, str]] = []
    new_items = 0

    with db.transaction() as conn:
        sent = {
            (r["report_code"], r["item_key"])
            for r in conn.execute("SELECT report_code, item_key FROM report_sent").fetchall()
        }

    for code, heading, fn, lines_fn in _SECTIONS:
        report = fn()
        degraded = degraded or bool(report.get("degraded"))
        fresh = [(key, line) for key, line in lines_fn(report) if (code, key) not in sent]
        if not fresh:
            continue
        new_items += len(fresh)
        blocks.append(heading + ":\n" + "\n".join(line for _, line in fresh))
        to_mark.extend((code, key) for key, _ in fresh)

    if mark and to_mark:
        with db.transaction() as conn:
            for code, key in to_mark:
                conn.execute(
                    """INSERT INTO report_sent (report_code, item_key) VALUES (%s, %s)
                       ON CONFLICT DO NOTHING""",
                    (code, key),
                )

    header = f"📋 Memoria organizației — {new_items} element(e) noi"
    if degraded:
        header += " ⚠ (Odoo indisponibil: liste posibil incomplete)"
    text = header + "\n\n" + "\n\n".join(blocks) if blocks else ""
    return {"text": text, "new_items": new_items, "degraded": degraded, "marked": bool(mark and to_mark)}
