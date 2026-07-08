"""Contractul adaptorului Odoo (plan §5) + poarta de scriere (§6).

Exact patru metode. Citirea punctuală = search_read cu [('id','in',ids)].
Poarta de scriere trăiește AICI (sursa unică a allowlist-ului) și în calea
unică _execute a implementărilor — nu prin convenție.
"""

from typing import Protocol

# Poarta de scriere (§6, invariantul I1). Sursa unică — importată de implementări și teste.
READ_METHODS = frozenset({"fields_get", "name_search", "search_read", "read", "search"})
WRITE_ALLOWLIST = frozenset({"message_post"})


class AdapterError(Exception):
    """Bază pentru erorile adaptorului."""


class AdapterUnavailable(AdapterError):
    """Conexiune/timeout — eroare transientă, retry permis pe citiri."""


class AdapterAccessDenied(AdapterError):
    """AccessError Odoo — drepturi insuficiente; nu se retry-uiește."""


class WriteGateViolation(AdapterError):
    """Metodă în afara allowlist-ului — ridicată ÎNAINTE de transportul RPC."""


class OdooAdapter(Protocol):
    def schema(self, model: str) -> dict[str, dict]:
        """fields_get: {field: {'type', 'string', 'relation'}}. Cache = viața procesului."""
        ...

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str],
        limit: int = 80,
        order: str | None = None,
        context: dict | None = None,
    ) -> list[dict]: ...

    def name_search(
        self,
        model: str,
        name: str,
        limit: int = 8,
        context: dict | None = None,
    ) -> list[tuple[int, str]]: ...

    def message_post(self, model: str, res_id: int, body: str) -> int:
        """SINGURA scriere permisă. body = text simplu (Odoo îl escapează).
        Întoarce mail_message_id. Zero retry intern."""
        ...


def check_gate(method: str) -> None:
    """Verificarea porții — apelată de ORICE implementare înainte de transport."""
    if method not in READ_METHODS and method not in WRITE_ALLOWLIST:
        raise WriteGateViolation(f"metoda '{method}' nu e în allowlist (R-001)")
