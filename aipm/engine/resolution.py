"""Rezoluția de entitate — SPEC §1.6, decisă operațional în plan A.§3 pasul 3.

Candidați = uniunea a două ramuri prin adaptor (semantică identică fake/real):
  (a) name_search;  (b) search_read cu OR-ilike peste resolution_fields (§1.2).
UN singur apel llm_rescore per item. Pragurile vin din anchor_type, nu din cod.
Zero candidați Odoo → scor 0 prin definiție (§1.6.2) → entitate externă (§1.7).
"""

import dataclasses
import json
import logging

import jsonschema

from ..adapter.contract import OdooAdapter
from . import llm
from .extraction import EntityMention, ExtractionInvalid, _call_with_repair

logger = logging.getLogger(__name__)

OWNER_TYPES = {"PARTNER", "EMPLOYEE"}  # SPEC §1.4, literă de lege

RESCORE_SCHEMA = {
    "type": "object",
    "required": ["scores"],
    "additionalProperties": False,
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["entity_index", "anchor_code", "res_id", "score"],
                "additionalProperties": False,
                "properties": {
                    "entity_index": {"type": "integer", "minimum": 0},
                    "anchor_code": {"type": "string"},
                    "res_id": {"type": "integer"},
                    "score": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
}
_RESCORE_VALIDATOR = jsonschema.Draft202012Validator(RESCORE_SCHEMA)


@dataclasses.dataclass
class ResolvedAnchor:
    role: str
    anchor_code: str
    odoo_res_id: int
    confidence: float
    needs_review: bool
    mention_text: str


@dataclasses.dataclass
class EntityResolution:
    """Rezultatul per entitate: exact una dintre cele trei stări."""

    entity: EntityMention
    anchor: ResolvedAnchor | None = None
    external: bool = False        # zero candidați Odoo pe toate tipurile (§1.7)
    drop_detail: str | None = None  # candidați există, scor sub review_threshold (§1.6.3)


def load_anchor_inventory(conn) -> list[dict]:
    rows = conn.execute(
        """SELECT code, odoo_model, label_ro, resolution_fields, disambiguation_fields,
                  has_chatter, url_template, accept_threshold, review_threshold, active
           FROM anchor_type WHERE active ORDER BY code"""
    ).fetchall()
    return [dict(r) for r in rows]


def load_kind_subject_matrix(conn) -> dict[str, set[str]]:
    rows = conn.execute("SELECT kind, anchor_code FROM kind_subject_allowed").fetchall()
    matrix: dict[str, set[str]] = {}
    for r in rows:
        matrix.setdefault(r["kind"], set()).add(r["anchor_code"])
    return matrix


def _candidate_types(
    entity: EntityMention,
    item_kind: str | None,
    inventory: list[dict],
    matrix: dict[str, set[str]],
) -> list[dict]:
    """Tipurile candidate per rol (plan A.§3 pasul 3 + §1.4)."""
    by_code = {a["code"]: a for a in inventory}
    if entity.role == "owner":
        allowed = OWNER_TYPES  # hint în afara setului = null (§1.4)
        if entity.anchor_code_hint in allowed:
            return [by_code[entity.anchor_code_hint]]
        return [by_code[c] for c in sorted(allowed) if c in by_code]
    if entity.anchor_code_hint and entity.anchor_code_hint in by_code:
        hinted = by_code[entity.anchor_code_hint]
        if entity.role != "subject" or item_kind is None or entity.anchor_code_hint in matrix.get(item_kind, set()):
            return [hinted]
    if entity.role == "subject" and item_kind is not None:
        return [by_code[c] for c in sorted(matrix.get(item_kind, set())) if c in by_code]
    return list(inventory)


def _search_candidates(adapter: OdooAdapter, atype: dict, text: str) -> list[dict]:
    """Uniunea dedup pe id a celor două ramuri (plan A.§3 pasul 3)."""
    model = atype["odoo_model"]
    ctx = {"active_test": False}  # arhivatele SUNT ancorabile (§1.6.1)
    seen: dict[int, dict] = {}
    for rid, display in adapter.name_search(model, text, limit=8, context=ctx):
        seen[rid] = {"id": rid, "display_name": display}
    fields = list(atype["resolution_fields"])
    domain: list = []
    for _ in range(len(fields) - 1):
        domain.append("|")
    for f in fields:
        domain.append((f, "ilike", text))
    rows = adapter.search_read(model, domain, fields + ["display_name"], limit=8, context=ctx)
    for row in rows:
        seen.setdefault(row["id"], {"id": row["id"], "display_name": row.get("display_name")})
        seen[row["id"]].update({k: v for k, v in row.items() if k != "id"})
    return list(seen.values())


def _rescore_prompt(entities_with_candidates: list[tuple[EntityMention, list[tuple[dict, dict]]]]) -> str:
    blocks = []
    for idx, (entity, candidates) in enumerate(entities_with_candidates):
        lines = [
            f"[{idx}] mentiune: '{entity.mention_text}' "
            f"(cautat: '{entity.normalized_text}', rol: {entity.role})"
        ]
        for atype, cand in candidates:
            extra = {k: v for k, v in cand.items() if k not in ("id", "display_name") and v}
            detail = f" detalii={extra}" if extra else ""
            lines.append(
                f"    candidat: anchor_code={atype['code']} res_id={cand['id']} "
                f"nume='{cand.get('display_name')}'{detail}"
            )
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def resolve_entities(
    conn,
    adapter: OdooAdapter,
    entities: list[EntityMention],
    item_kind: str | None,
    context_text: str = "",
) -> list[EntityResolution]:
    """Rezolvă entitățile UNUI item (sau ale unei întrebări, item_kind=None)."""
    inventory = load_anchor_inventory(conn)
    matrix = load_kind_subject_matrix(conn)
    results = [EntityResolution(entity=e) for e in entities]

    with_candidates: list[tuple[int, list[tuple[dict, dict]]]] = []
    for i, res in enumerate(results):
        candidates: list[tuple[dict, dict]] = []
        for atype in _candidate_types(res.entity, item_kind, inventory, matrix):
            for cand in _search_candidates(adapter, atype, res.entity.normalized_text):
                candidates.append((atype, cand))
        if not candidates:
            res.external = True  # scor 0 prin definiție (§1.6.2) → §1.7
        else:
            with_candidates.append((i, candidates))

    if not with_candidates:
        return results

    # UN singur apel de rescorare per item (plan A.§3 pasul 3)
    system = (
        "Rescorezi candidați Odoo pentru mențiuni de entități dintr-un mesaj de lucru. "
        "Pentru FIECARE candidat listat, dă un scor 0..1 = probabilitatea ca acel candidat "
        "să fie exact entitatea menționată. Folosește detaliile (proiect, oraș, cod, stare). "
        "Nu inventa res_id-uri care nu sunt în listă."
    )
    prompt_entities = [(results[i].entity, cands) for i, cands in with_candidates]
    user = (
        (f"Context (mesajul-sursă):\n{context_text[:1500]}\n\n" if context_text else "")
        + "Mențiuni și candidați:\n"
        + _rescore_prompt(prompt_entities)
    )
    try:
        data = _call_with_repair(llm.rescore_json, system, user, _RESCORE_VALIDATOR)
    except ExtractionInvalid as e:
        logger.warning("rescore invalid după retry: %s", e)
        for i, _ in with_candidates:
            results[i].drop_detail = "rescore_invalid"
        return results

    # cel mai bun candidat per entitate, DOAR dintre candidații reali (anti-halucinare id)
    allowed: dict[int, set[tuple[str, int]]] = {}
    for pos, (i, cands) in enumerate(with_candidates):
        allowed[pos] = {(atype["code"], cand["id"]) for atype, cand in cands}
    best: dict[int, tuple[str, int, float]] = {}
    for s in data["scores"]:
        pos = s["entity_index"]
        if pos not in allowed or (s["anchor_code"], s["res_id"]) not in allowed[pos]:
            continue
        if pos not in best or s["score"] > best[pos][2]:
            best[pos] = (s["anchor_code"], s["res_id"], s["score"])

    by_code = {a["code"]: a for a in inventory}
    for pos, (i, _) in enumerate(with_candidates):
        res = results[i]
        if pos not in best:
            res.drop_detail = "rescore_missing"
            continue
        code, rid, score = best[pos]
        atype = by_code[code]
        accept, review = float(atype["accept_threshold"]), float(atype["review_threshold"])
        if score >= accept:
            res.anchor = ResolvedAnchor(res.entity.role, code, rid, score, False, res.entity.mention_text)
        elif score >= review:
            res.anchor = ResolvedAnchor(res.entity.role, code, rid, score, True, res.entity.mention_text)
        else:
            # candidați EXISTĂ dar scor sub review → NU ancoră, NU externă (§1.6.3 + plan pasul 6)
            res.drop_detail = f"sub_prag:{code}:{rid}:{score:.2f}"
    return results


def resolve_question_entities(
    conn, adapter: OdooAdapter, entities: list[EntityMention], min_score: float = 0.50
) -> list[ResolvedAnchor]:
    """Rezoluția pe ÎNTREBARE (recall §4 pasul 1): fără praguri de scriere, reține ≥ min_score."""
    inventory = load_anchor_inventory(conn)
    matrix: dict[str, set[str]] = {}
    results = [EntityResolution(entity=e) for e in entities]
    with_candidates: list[tuple[int, list[tuple[dict, dict]]]] = []
    for i, res in enumerate(results):
        candidates: list[tuple[dict, dict]] = []
        for atype in _candidate_types(res.entity, None, inventory, matrix):
            for cand in _search_candidates(adapter, atype, res.entity.normalized_text):
                candidates.append((atype, cand))
        if candidates:
            with_candidates.append((i, candidates))
    if not with_candidates:
        return []
    system = (
        "Rescorezi candidați Odoo pentru entitățile menționate într-o întrebare. "
        "Scor 0..1 per candidat listat; nu inventa res_id-uri."
    )
    user = "Mențiuni și candidați:\n" + _rescore_prompt(
        [(results[i].entity, cands) for i, cands in with_candidates]
    )
    try:
        data = _call_with_repair(llm.rescore_json, system, user, _RESCORE_VALIDATOR)
    except ExtractionInvalid:
        return []
    allowed: dict[int, set[tuple[str, int]]] = {
        pos: {(a["code"], c["id"]) for a, c in cands}
        for pos, (_, cands) in enumerate(with_candidates)
    }
    best: dict[int, tuple[str, int, float]] = {}
    for s in data["scores"]:
        pos = s["entity_index"]
        if pos not in allowed or (s["anchor_code"], s["res_id"]) not in allowed[pos]:
            continue
        if pos not in best or s["score"] > best[pos][2]:
            best[pos] = (s["anchor_code"], s["res_id"], s["score"])
    out = []
    for pos, (i, _) in enumerate(with_candidates):
        if pos in best and best[pos][2] >= min_score:
            code, rid, score = best[pos]
            out.append(
                ResolvedAnchor("mentions", code, rid, score, False, results[i].entity.mention_text)
            )
    return out
