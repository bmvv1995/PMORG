"""Grefierul — extracția structurată din mesaje-sursă (SPEC §2, decis în plan A.§2).

Un apel LLM per mesaj → items validate cu JSON Schema strict, apoi normalizate
determinist în cod. JSON invalid → UN retry de reparare → ExtractionInvalid.
"""

import dataclasses
import json
import logging
import unicodedata
from datetime import date, datetime

import jsonschema

from .. import config
from . import llm

logger = logging.getLogger(__name__)

KINDS = ["decision", "commitment", "observation", "open_question", "rule_candidate"]

KIND_RO = {
    "decision": "decizie",
    "commitment": "angajament",
    "observation": "observație",
    "open_question": "întrebare deschisă",
    "rule_candidate": "candidat de regulă",
}

_ENTITY_SCHEMA = {
    "type": "object",
    "required": ["role", "mention_text", "normalized_text", "anchor_code_hint"],
    "additionalProperties": False,
    "properties": {
        "role": {"enum": ["subject", "owner", "mentions"]},
        "mention_text": {"type": "string", "maxLength": 200},
        "normalized_text": {"type": "string", "maxLength": 200},
        "anchor_code_hint": {"type": ["string", "null"]},
    },
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "required": ["items"],
    "additionalProperties": False,
    "properties": {
        "items": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": ["kind", "title", "body", "quote", "confidence", "entities"],
                "additionalProperties": False,
                "properties": {
                    "kind": {"enum": KINDS},
                    "title": {"type": "string", "minLength": 3, "maxLength": 140},
                    "body": {"type": "string", "minLength": 3, "maxLength": 2000},
                    "quote": {"type": "string", "maxLength": 500},
                    "due_at": {"type": ["string", "null"], "format": "date"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "entities": {"type": "array", "maxItems": 10, "items": _ENTITY_SCHEMA},
                },
            },
        }
    },
}

QUERY_SCHEMA = {
    "type": "object",
    "required": ["entities"],
    "additionalProperties": False,
    "properties": {
        "entities": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": ["mention_text", "normalized_text", "anchor_code_hint"],
                "additionalProperties": False,
                "properties": {
                    "mention_text": {"type": "string", "maxLength": 200},
                    "normalized_text": {"type": "string", "maxLength": 200},
                    "anchor_code_hint": {"type": ["string", "null"]},
                },
            },
        }
    },
}

_DATE_VALIDATOR = jsonschema.Draft202012Validator(
    EXTRACTION_SCHEMA, format_checker=jsonschema.FormatChecker()
)
_QUERY_VALIDATOR = jsonschema.Draft202012Validator(
    QUERY_SCHEMA, format_checker=jsonschema.FormatChecker()
)


class ExtractionInvalid(Exception):
    """Output invalid și după retry-ul de reparare → ingest_log 'extract_failed'."""


@dataclasses.dataclass
class EntityMention:
    role: str
    mention_text: str
    normalized_text: str
    anchor_code_hint: str | None


@dataclasses.dataclass
class ExtractedItem:
    kind: str
    title: str
    body: str
    quote: str
    due_at: date | None
    confidence: float
    entities: list[EntityMention]


def unaccent(text: str) -> str:
    """Pliere diacritice — folosită la content_hash și normalized_text."""
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if not unicodedata.combining(c))


def _system_prompt(anchor_inventory: list[dict]) -> str:
    codes = "\n".join(
        f"  - {a['code']}: {a['label_ro']} (model Odoo: {a['odoo_model']})"
        for a in anchor_inventory
        if a.get("active", True)
    )
    return f"""Ești grefierul unui sistem de memorie organizațională ancorat în Odoo.
Primești UN mesaj dintr-o conversație de lucru (chatter Odoo sau chat intern) și extragi
elementele de memorie: ce merită ținut minte dincolo de datele deja înregistrate în ERP.

Tipuri (kind):
  - decision: o decizie luată explicit
  - commitment: cineva s-a angajat să facă ceva (owner = cine datorează)
  - observation: constatare factuală relevantă
  - open_question: întrebare/dilemă rămasă deschisă
  - rule_candidate: o regulă de lucru implicită care ar merita formalizată

Tipurile de ancoră disponibile (anchor_code_hint doar din această listă, altfel null):
{codes}

Reguli stricte:
- title/body/quote în ROMÂNĂ; body = reformulare auto-conținută (inteligibilă fără mesaj);
  quote = citat VERBATIM din mesaj (proveniența).
- due_at DOAR dacă un termen e explicit în text (format YYYY-MM-DD); NU inventa termene.
- Exact o entitate cu role=subject per item (despre ce e amintirea).
- role=owner doar la commitment (cine datorează — persoană sau partener).
- normalized_text = numele curat, căutabil în Odoo (fără „cel de la", fără flexiuni).
- confidence = cât de sigur ești că itemul e o consemnare reală, nu conversație de umplutură.
- Dacă mesajul nu conține nimic memorabil → {{"items": []}}."""


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
    return json.loads(raw)


def _validated(raw: str, validator) -> dict:
    data = _parse_json(raw)
    validator.validate(data)
    return data


def _call_with_repair(call, system: str, user: str, validator) -> dict:
    raw = call(system, user)
    try:
        return _validated(raw, validator)
    except (json.JSONDecodeError, jsonschema.ValidationError) as first_err:
        repair_user = (
            f"{user}\n\nRăspunsul tău anterior a fost INVALID:\n{raw[:2000]}\n\n"
            f"Eroarea validatorului: {first_err}\nTrimite din nou JSON-ul corectat."
        )
        raw2 = call(system, repair_user)
        try:
            return _validated(raw2, validator)
        except (json.JSONDecodeError, jsonschema.ValidationError) as second_err:
            raise ExtractionInvalid(str(second_err)) from second_err


def _normalize_items(data: dict, anchor_inventory: list[dict]) -> list[ExtractedItem]:
    """Regulile deterministe din plan A.§2 — aplicate DUPĂ validarea schemei."""
    valid_codes = {a["code"] for a in anchor_inventory if a.get("active", True)}
    raw_items = sorted(data["items"], key=lambda i: -i["confidence"])[:5]
    items: list[ExtractedItem] = []
    for raw in raw_items:
        if raw["confidence"] < config.EXTRACT_MIN_CONFIDENCE:
            continue
        due_at = None
        if raw["kind"] == "commitment" and raw.get("due_at"):
            due_at = datetime.strptime(raw["due_at"], "%Y-%m-%d").date()
        entities: list[EntityMention] = []
        seen_subject = False
        seen_owner = False
        for e in raw["entities"]:
            role = e["role"]
            hint = e["anchor_code_hint"]
            if hint is not None and hint not in valid_codes:
                hint = None
            if role == "subject":
                if seen_subject:
                    role = "mentions"
                seen_subject = True
            elif role == "owner":
                if raw["kind"] != "commitment" or seen_owner:
                    role = "mentions"
                else:
                    seen_owner = True
            entities.append(
                EntityMention(
                    role=role,
                    mention_text=e["mention_text"],
                    normalized_text=e["normalized_text"],
                    anchor_code_hint=hint,
                )
            )
        items.append(
            ExtractedItem(
                kind=raw["kind"],
                title=raw["title"],
                body=raw["body"],
                quote=raw["quote"][:500],
                due_at=due_at,
                confidence=raw["confidence"],
                entities=entities,
            )
        )
    return items


def extract(
    source_text: str,
    author_name: str | None,
    author_partner_id: int | None,
    msg_date: datetime,
    anchor_inventory: list[dict],
) -> list[ExtractedItem]:
    """Poate ridica ExtractionInvalid (terminal) sau llm.LLMTransientError (retry natural)."""
    user = (
        f"Autor: {author_name or 'necunoscut'}"
        f"{f' (res.partner #{author_partner_id})' if author_partner_id else ''}\n"
        f"Data: {msg_date:%Y-%m-%d %H:%M}\n\nMesaj:\n{source_text[:config.MAX_SOURCE_CHARS]}"
    )
    data = _call_with_repair(llm.extract_json, _system_prompt(anchor_inventory), user, _DATE_VALIDATOR)
    return _normalize_items(data, anchor_inventory)


def extract_query_entities(question: str, anchor_inventory: list[dict]) -> list[EntityMention]:
    """Entitățile dintr-o ÎNTREBARE (recall §4 pasul 1). Eșec → listă goală, nu excepție."""
    codes = ", ".join(a["code"] for a in anchor_inventory if a.get("active", True))
    system = (
        "Extragi entitățile Odoo menționate într-o întrebare de lucru (proiecte, taskuri, "
        f"parteneri, angajați, comenzi, oportunități, produse). anchor_code_hint ∈ {{{codes}}} sau null. "
        'normalized_text = numele curat, căutabil. Fără entități → {"entities": []}.'
    )
    try:
        data = _call_with_repair(llm.query_entities_json, system, question, _QUERY_VALIDATOR)
    except ExtractionInvalid:
        logger.warning("extract_query_entities: JSON invalid după retry — set structural gol")
        return []
    valid_codes = {a["code"] for a in anchor_inventory if a.get("active", True)}
    return [
        EntityMention(
            role="mentions",
            mention_text=e["mention_text"],
            normalized_text=e["normalized_text"],
            anchor_code_hint=e["anchor_code_hint"] if e["anchor_code_hint"] in valid_codes else None,
        )
        for e in data["entities"]
    ]
