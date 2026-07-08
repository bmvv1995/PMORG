"""FakeOdooAdapter — implementare first-class pentru dev/teste (plan §5).

Fixtures JSON per model (adapter/fixtures/<model>.json), chatter fals in-memory
interogabil prin search_read('mail.message', ...), injecție de defecte fail_next.
Trece prin ACEEAȘI poartă de scriere ca adaptorul real (check_gate în _execute).
"""

import html
import json
import pathlib
from datetime import datetime

from .contract import check_gate

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"

# Metadate de fixture: comodel-urile câmpurilor x2many (realul le ia din fields_get)
RELATIONS = {
    ("project.task", "user_ids"): "res.partner",
    ("project.task", "project_id"): "project.project",
    ("project.project", "user_id"): "res.partner",
    ("purchase.order", "partner_id"): "res.partner",
    ("sale.order", "partner_id"): "res.partner",
    ("product.template", "categ_id"): "product.category",
    ("hr.employee", "department_id"): "hr.department",
}


def _m2o_id(value):
    """Valorile many2one sunt [id, display_name] — comparațiile folosesc id-ul."""
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return value


def _norm(cond_value):
    if isinstance(cond_value, datetime):
        return cond_value.strftime("%Y-%m-%d %H:%M:%S")
    return cond_value


def _match_condition(record: dict, cond) -> bool:
    field, op, value = cond
    raw = record.get(field, False)
    rec_val = _m2o_id(raw)
    value = _norm(value)
    if op == "=":
        return rec_val == value
    if op == "!=":
        return rec_val != value
    if op == "in":
        return rec_val in value
    if op == "not in":
        return rec_val not in value
    if op == "ilike":
        return isinstance(rec_val, str) and str(value).lower() in rec_val.lower()
    if op in (">", ">=", "<", "<="):
        if rec_val is False or rec_val is None:
            return False
        try:
            if op == ">":
                return rec_val > value
            if op == ">=":
                return rec_val >= value
            if op == "<":
                return rec_val < value
            return rec_val <= value
        except TypeError:
            return False
    raise ValueError(f"operator de domeniu nesuportat în fake: {op}")


def _eval_domain(record: dict, domain: list) -> bool:
    """Notație poloneză Odoo: '&', '|', '!' + AND implicit între termeni."""

    def parse(i: int):
        token = domain[i]
        if token == "&":
            left, i = parse(i + 1)
            right, i = parse(i)
            return left and right, i
        if token == "|":
            left, i = parse(i + 1)
            right, i = parse(i)
            return left or right, i
        if token == "!":
            val, i = parse(i + 1)
            return not val, i
        return _match_condition(record, token), i + 1

    result, i = True, 0
    while i < len(domain):
        val, i = parse(i)
        result = result and val
    return result


class FakeOdooAdapter:
    def __init__(self, fixtures_dir: pathlib.Path = FIXTURES_DIR):
        self._data: dict[str, list[dict]] = {}
        for path in sorted(fixtures_dir.glob("*.json")):
            self._data[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        self._data.setdefault("mail.message", [])
        self._msg_seq = max((m["id"] for m in self._data["mail.message"]), default=1000)
        self._failures: dict[str, list[Exception]] = {}

    # --- injecție de defecte (plan §5) ---
    def fail_next(self, method: str, exc: Exception, times: int = 1) -> None:
        self._failures.setdefault(method, []).extend([exc] * times)

    def _maybe_fail(self, method: str) -> None:
        queue = self._failures.get(method)
        if queue:
            raise queue.pop(0)

    # --- calea unică (aceeași poartă ca realul) ---
    def _execute(self, model: str, method: str):
        check_gate(method)
        self._maybe_fail(method)
        return self._data.setdefault(model, [])

    # --- helpers ---
    @staticmethod
    def _display_name(record: dict) -> str:
        return record.get("display_name") or record.get("name") or f"#{record['id']}"

    def _visible(self, records: list[dict], context: dict | None) -> list[dict]:
        active_test = (context or {}).get("active_test", True)
        if active_test:
            return [r for r in records if r.get("active", True)]
        return records

    # --- contractul ---
    def schema(self, model: str) -> dict[str, dict]:
        records = self._execute(model, "fields_get")
        fields: dict[str, dict] = {}
        for record in records:
            for key, value in record.items():
                if key in fields:
                    continue
                relation = RELATIONS.get((model, key), "")
                if isinstance(value, (list, tuple)) and len(value) == 2 and isinstance(value[0], int):
                    fields[key] = {"type": "many2one", "string": key, "relation": relation}
                elif isinstance(value, list):
                    fields[key] = {"type": "one2many", "string": key, "relation": relation}
                elif isinstance(value, bool):
                    fields[key] = {"type": "boolean", "string": key, "relation": None}
                elif isinstance(value, (int, float)):
                    fields[key] = {"type": "float", "string": key, "relation": None}
                else:
                    fields[key] = {"type": "char", "string": key, "relation": None}
        return fields

    def search_read(self, model, domain, fields, limit=80, order=None, context=None):
        records = self._visible(self._execute(model, "search_read"), context)
        matched = [r for r in records if _eval_domain(r, domain)]
        if order:
            key, _, direction = order.partition(" ")
            matched.sort(key=lambda r: _m2o_id(r.get(key)) or 0, reverse=direction.strip() == "desc")
        matched = matched[:limit]
        out = []
        for r in matched:
            row = {"id": r["id"]}
            for f in fields:
                row[f] = self._display_name(r) if f == "display_name" else r.get(f, False)
            out.append(row)
        return out

    def name_search(self, model, name, limit=8, context=None):
        records = self._visible(self._execute(model, "name_search"), context)
        needle = name.lower()
        hits = [r for r in records if needle in self._display_name(r).lower()]
        return [(r["id"], self._display_name(r)) for r in hits[:limit]]

    def message_post(self, model: str, res_id: int, body: str) -> int:
        self._execute(model, "message_post")  # poarta + defecte
        self._msg_seq += 1
        self._data["mail.message"].append(
            {
                "id": self._msg_seq,
                "model": model,
                "res_id": res_id,
                "author_id": [self.service_partner_id(), "AIPM Service"],
                # Odoo escapează body-urile str — simulăm fidel (plan §3 pasul 7)
                "body": "<p>" + html.escape(body).replace("\n", "<br>") + "</p>",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message_type": "comment",
            }
        )
        return self._msg_seq

    def service_partner_id(self) -> int:
        users = self._data.get("res.users", [])
        for u in users:
            if u.get("login") == "aipm":
                return _m2o_id(u["partner_id"])
        return 0

    # --- helper de test: mesaj „uman" în chatter-ul fals ---
    def add_chatter_message(
        self, model: str, res_id: int, body: str, author_id: int, author_name: str,
        date: str | None = None,
    ) -> int:
        self._msg_seq += 1
        self._data["mail.message"].append(
            {
                "id": self._msg_seq,
                "model": model,
                "res_id": res_id,
                "author_id": [author_id, author_name],
                "body": f"<p>{html.escape(body)}</p>",
                "date": date or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message_type": "comment",
            }
        )
        return self._msg_seq
