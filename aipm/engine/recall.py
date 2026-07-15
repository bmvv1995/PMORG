"""Pipeline-ul de citire — plan A.§4.

Fuziune prin COTE (nu adunare de scoruri), precedență absolută a citirii live
din Odoo (mulțimea S), post-validare mecanică a claims-urilor (I2).
Sesiuni in-memory (limitare v1 documentată).
"""

import collections
import json
import logging
import threading
import uuid as uuid_mod

import jsonschema

from .. import config, db
from ..adapter import get_adapter
from ..adapter.contract import AdapterError
from . import embeddings, llm, resolution
from .extraction import ExtractionInvalid, _call_with_repair, extract_query_entities

logger = logging.getLogger(__name__)

# --- Sesiuni: dict in-memory, pierdute la restart (plan A.§4 pasul 0) ---
_sessions: dict[str, collections.deque] = {}
_sessions_lock = threading.Lock()


def get_session(session_id: str | None) -> tuple[str, collections.deque]:
    with _sessions_lock:
        if session_id is None or session_id not in _sessions:
            session_id = session_id or str(uuid_mod.uuid4())
            _sessions[session_id] = collections.deque(maxlen=config.SESSION_MAX_TURNS)
        return session_id, _sessions[session_id]


NARRATE_SCHEMA = {
    "type": "object",
    "required": ["answer_ro", "claims"],
    "additionalProperties": False,
    "properties": {
        "answer_ro": {"type": "string"},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["text", "status", "support"],
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "status": {"enum": ["fact", "hypothesis"]},
                    "support": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type"],
                            "additionalProperties": False,
                            "properties": {
                                "type": {"enum": ["odoo", "memory"]},
                                "anchor_code": {"type": "string"},
                                "res_id": {"type": "integer"},
                                "field": {"type": "string"},
                                "value": {"type": "string"},
                                "memory_id": {"type": "string"},
                                "kind": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}
_NARRATE_VALIDATOR = jsonschema.Draft202012Validator(NARRATE_SCHEMA)


def serialize_odoo_value(field: str, value) -> str:
    """Funcția canonică UNICĂ de serializare (plan A.§4 pasul 6) — aceeași la
    construirea mulțimii S și la validarea suporturilor."""
    if value is None or value is False:
        return ""
    if isinstance(value, (list, tuple)):
        if len(value) == 2 and isinstance(value[0], int) and isinstance(value[1], str):
            return value[1]  # many2one → display_name
        return ", ".join(str(v) for v in value)
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def fetch_live(conn, adapter, anchor_refs: set[tuple[str, int]]):
    """Citirea live Odoo (plan A.§4 pasul 5): singura sursă de stare curentă.

    Returnează (rows, S, deleted):
      rows[(code, rid)] = {field: value_str}   — pentru context și UI
      S = {(code, rid, field, value_str)}      — mulțimea de validare (I2)
      deleted = {(code, rid)}                  — chip „⚠ ștearsă" (§1.9)
    """
    types = {a["code"]: a for a in resolution.load_anchor_inventory(conn)}
    rows: dict[tuple[str, int], dict[str, str]] = {}
    S: set[tuple[str, int, str, str]] = set()
    deleted: set[tuple[str, int]] = set()

    by_code: dict[str, list[int]] = {}
    for code, rid in anchor_refs:
        by_code.setdefault(code, []).append(rid)

    for code, ids in by_code.items():
        atype = types.get(code)
        if atype is None:
            continue
        model = atype["odoo_model"]
        disamb = list(atype["disambiguation_fields"])
        direct = [f for f in disamb if "." not in f]
        dotted = [f for f in disamb if "." in f]
        request_fields = ["display_name"] + direct + sorted({f.split(".")[0] for f in dotted})
        try:
            fetched = adapter.search_read(
                model, [("id", "in", ids)], request_fields,
                limit=len(ids), context={"active_test": False},
            )
        except AdapterError as e:
            logger.warning("fetch_live a eșuat pe %s: %s", model, e)
            continue
        found = {r["id"]: r for r in fetched}
        schema = adapter.schema(model)
        for rid in ids:
            key = (code, rid)
            if rid not in found:
                deleted.add(key)
                continue
            raw = found[rid]
            out: dict[str, str] = {}
            for f in ["display_name"] + direct:
                out[f] = serialize_odoo_value(f, raw.get(f))
            for f in dotted:
                base = f.split(".")[0]
                value = raw.get(base)
                if isinstance(value, list) and value and all(isinstance(v, int) for v in value):
                    comodel = (schema.get(base) or {}).get("relation")
                    if comodel:
                        try:
                            names = adapter.search_read(
                                comodel, [("id", "in", value)], ["display_name"],
                                limit=len(value), context={"active_test": False},
                            )
                            out[f] = ", ".join(n["display_name"] for n in names)
                        except AdapterError:
                            out[f] = serialize_odoo_value(f, value)
                    else:
                        out[f] = serialize_odoo_value(f, value)
                else:
                    out[f] = serialize_odoo_value(f, value)  # m2o → display_name din tuplu
            rows[key] = out
            for f, v in out.items():
                S.add((code, rid, f, v))
    return rows, S, deleted


def _anchor_url(atype: dict, res_id: int) -> str:
    return atype["url_template"].format(
        base_url=config.ODOO_BASE_URL, odoo_model=atype["odoo_model"], odoo_res_id=res_id
    )


def _postvalidate_claims(claims: list[dict], S, memory_ids: set[str], deleted, types) -> list[dict]:
    """Apărarea mecanică anti-halucinație (I2) — în cod, nu în prompt."""
    out = []
    for claim in claims:
        supports = []
        for s in claim.get("support", []):
            if s.get("type") == "odoo":
                key = (s.get("anchor_code"), s.get("res_id"), s.get("field"), s.get("value"))
                if key in S:
                    atype = types.get(s["anchor_code"])
                    supports.append(
                        s | {
                            "url": _anchor_url(atype, s["res_id"]) if atype else None,
                            "deleted": (s["anchor_code"], s["res_id"]) in deleted,
                        }
                    )
            elif s.get("type") == "memory" and s.get("memory_id") in memory_ids:
                supports.append(s)
        if not supports:
            continue  # claim fără suport valid → eliminat din payload
        has_odoo = any(s["type"] == "odoo" for s in supports)
        out.append(
            {
                "text": claim["text"],
                "status": "fact" if has_odoo else "hypothesis",  # forțat de cod
                "support": supports,
            }
        )
    return out


def answer(question: str, session_id: str | None) -> dict:
    adapter = get_adapter()
    session_id, turns = get_session(session_id)
    degraded = False

    history = "\n".join(f"User: {q}\nAsistent: {a}" for q, a in turns)
    context_question = f"{history}\n{question}" if history else question

    with db.transaction() as conn:
        inventory = resolution.load_anchor_inventory(conn)
        types = {a["code"]: a for a in inventory}

        # 1. entități din întrebare (+ ancorele tururilor anterioare ca hint-uri)
        try:
            entities = extract_query_entities(context_question, inventory)
        except llm.LLMTransientError:
            entities = []
        question_anchors = (
            resolution.resolve_question_entities(conn, adapter, entities) if entities else []
        )
        anchor_refs = {(a.anchor_code, a.odoo_res_id) for a in question_anchors}

        # 2. recall structural
        structural: list[dict] = []
        if anchor_refs:
            conditions = " OR ".join(
                ["(ma.anchor_code = %s AND ma.odoo_res_id = %s)"] * len(anchor_refs)
            )
            params: list = []
            for code, rid in anchor_refs:
                params.extend([code, rid])
            structural = [
                dict(r)
                for r in conn.execute(
                    f"""SELECT DISTINCT mi.id, mi.kind, mi.title, mi.body, mi.due_at,
                               mi.trust, mi.created_at
                        FROM memory_item mi JOIN memory_anchor ma ON ma.memory_id = mi.id
                        WHERE mi.status = 'active' AND ({conditions})
                        ORDER BY mi.created_at DESC LIMIT 20""",
                    params,
                ).fetchall()
            ]

        # 3. recall semantic
        semantic: list[dict] = []
        try:
            qvec = embeddings.embed_one(context_question)
            semantic = [
                dict(r)
                for r in conn.execute(
                    """SELECT id, kind, title, body, due_at, trust, created_at,
                              1 - (embedding <=> %s::vector) AS similarity
                       FROM memory_item
                       WHERE status = 'active' AND embedding IS NOT NULL
                         AND 1 - (embedding <=> %s::vector) >= %s
                       ORDER BY embedding <=> %s::vector LIMIT %s""",
                    (qvec, qvec, config.RECALL_MIN_SIM, qvec, config.RECALL_TOP_K),
                ).fetchall()
            ]
        except embeddings.EmbeddingUnavailable:
            degraded = True

        # 4. fuziune prin cote (plan A.§4 pasul 4): structural deja ordonat created_at DESC
        struct_slot = structural[: config.RECALL_STRUCT_SLOTS]
        chosen: dict[str, dict] = {str(r["id"]): r for r in struct_slot}
        for r in semantic:
            if len(chosen) >= config.RECALL_TOP_K:
                break
            chosen.setdefault(str(r["id"]), r)
        if len(chosen) < config.RECALL_TOP_K:  # sloturile nefolosite curg înapoi
            for r in structural:
                if len(chosen) >= config.RECALL_TOP_K:
                    break
                chosen.setdefault(str(r["id"]), r)
        memory_items = list(chosen.values())
        memory_ids = set(chosen.keys())

        # ancorele itemilor aleși intră și ele în citirea live
        if memory_ids:
            anchor_rows = conn.execute(
                "SELECT DISTINCT anchor_code, odoo_res_id FROM memory_anchor WHERE memory_id = ANY(%s::uuid[])",
                (list(memory_ids),),
            ).fetchall()
            anchor_refs |= {(r["anchor_code"], r["odoo_res_id"]) for r in anchor_rows}

        # 5. Odoo live — precedență absolută
        odoo_rows, S, deleted = fetch_live(conn, adapter, anchor_refs)

    # 6. narare
    odoo_block = (
        "\n".join(
            f"- {code} #{rid} ({types[code]['label_ro']}): "
            + "; ".join(f"{f}={v}" for f, v in fields.items() if v)
            for (code, rid), fields in odoo_rows.items()
        )
        or "(nimic găsit în Odoo)"
    )
    deleted_block = "\n".join(f"- {code} #{rid}: ȘTEARSĂ din Odoo" for code, rid in deleted)
    memory_block = (
        "\n".join(
            f"- memory_id={mid} kind={m['kind']} trust={m['trust']}: {m['title']} — {m['body']}"
            for mid, m in chosen.items()
        )
        or "(memoria nu conține nimic relevant)"
    )
    system = (
        "Ești AI-PM: asistentul de management ancorat în Odoo al unei companii horeca. "
        "Răspunzi în ROMÂNĂ, cald și concis.\n"
        "REGULI DE ADEVĂR (obligatorii):\n"
        "- Starea CURENTĂ vine EXCLUSIV din blocul [ODOO]; memoria ([MEMORIE]) e context istoric.\n"
        "- Orice afirmație factuală o pui în claims[]: cu suport odoo (copiezi anchor_code/res_id/"
        "field/value VERBATIM din [ODOO]) → status=fact; doar cu suport memory → status=hypothesis.\n"
        "- Ce nu poți susține nu afirmi — formulezi ca întrebare în answer_ro.\n"
        "- Ipotezele din memorie au voie să sugereze și să întrebe, niciodată să afirme."
    )
    user = (
        f"[ODOO]\n{odoo_block}\n"
        + (f"\n[ȘTERSE]\n{deleted_block}\n" if deleted_block else "")
        + f"\n[MEMORIE]\n{memory_block}\n"
        + (f"\n[CONVERSAȚIE]\n{history}\n" if history else "")
        + f"\nÎntrebarea: {question}"
    )
    try:
        data = _call_with_repair(llm.narrate_json, system, user, _NARRATE_VALIDATOR)
    except ExtractionInvalid:
        data = {
            "answer_ro": "Nu am putut formula un răspuns valid acum — încearcă să reformulezi.",
            "claims": [],
        }
    except llm.LLMTransientError:
        data = {"answer_ro": "Serviciul LLM e temporar indisponibil.", "claims": []}

    # 7. post-validare (I2)
    claims = _postvalidate_claims(data["claims"], S, memory_ids, deleted, types)

    turns.append((question, data["answer_ro"]))

    # 8. jurnalul (etapa 10, P5): latura de ASISTENT, append-only, în carantină.
    # Latura de utilizator verbatim așteaptă poarta de intimitate (etapa 4).
    try:
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO chat_turn (session_id, role, body, degraded) VALUES (%s,'assistant',%s,%s)",
                (session_id, data["answer_ro"], degraded),
            )
    except Exception:
        logger.exception("jurnalizarea turului de asistent a eșuat (răspunsul pleacă oricum)")

    return {
        "session_id": session_id,
        "answer_ro": data["answer_ro"],
        "claims": claims,
        "degraded": degraded,
    }
