"""Adaptorul Odoo real — xmlrpc.client peste /xmlrpc/2 (plan §5).

Toate apelurile trec prin calea unică _execute, unde poarta de scriere (§6)
se aplică ÎNAINTE de transport. Cache doar pe schema(); restul se citește live (§1.9).
"""

import logging
import socket
import time
import xmlrpc.client

from .. import config
from .contract import (
    AdapterAccessDenied,
    AdapterUnavailable,
    check_gate,
)

logger = logging.getLogger(__name__)

_TRANSIENT_RETRIES = 2
_BACKOFFS = (1.0, 3.0)


class XmlRpcOdooAdapter:
    def __init__(self):
        self._uid: int | None = None
        self._schema_cache: dict[str, dict] = {}
        self._common = xmlrpc.client.ServerProxy(
            f"{config.ODOO_RPC_URL}/xmlrpc/2/common", allow_none=True
        )
        self._object = xmlrpc.client.ServerProxy(
            f"{config.ODOO_RPC_URL}/xmlrpc/2/object", allow_none=True
        )

    # --- autentificare lazy ---
    def _authenticate(self) -> int:
        uid = self._common.authenticate(
            config.ODOO_DB, config.ODOO_RPC_LOGIN, config.ODOO_RPC_PASSWORD, {}
        )
        if not uid:
            raise AdapterAccessDenied("autentificare eșuată pentru utilizatorul de serviciu")
        return uid

    def _uid_or_login(self) -> int:
        if self._uid is None:
            self._uid = self._authenticate()
        return self._uid

    # --- calea unică: poarta + transport + erori tipizate ---
    def _execute(self, model: str, method: str, args: list, kwargs: dict | None = None):
        check_gate(method)  # I1: înainte de transport
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(config.RPC_TIMEOUT_SECONDS)
        try:
            return self._object.execute_kw(
                config.ODOO_DB,
                self._uid_or_login(),
                config.ODOO_RPC_PASSWORD,
                model,
                method,
                args,
                kwargs or {},
            )
        except xmlrpc.client.Fault as e:
            fault = str(e.faultString or "")
            if "AccessError" in fault or "AccessDenied" in fault:
                raise AdapterAccessDenied(fault) from e
            if "SessionExpired" in fault:
                # o singură re-autentificare per apel
                self._uid = None
                return self._execute(model, method, args, kwargs)
            raise AdapterUnavailable(fault) from e
        except (OSError, xmlrpc.client.ProtocolError) as e:
            raise AdapterUnavailable(str(e)) from e
        finally:
            socket.setdefaulttimeout(old_timeout)

    def _execute_read(self, model: str, method: str, args: list, kwargs: dict | None = None):
        """Citiri: 2 retry cu backoff pe erori transiente (§5)."""
        for attempt in range(_TRANSIENT_RETRIES + 1):
            try:
                return self._execute(model, method, args, kwargs)
            except AdapterUnavailable:
                if attempt == _TRANSIENT_RETRIES:
                    raise
                time.sleep(_BACKOFFS[attempt])

    # --- contractul ---
    def schema(self, model: str) -> dict[str, dict]:
        if model not in self._schema_cache:
            fields = self._execute_read(
                model, "fields_get", [], {"attributes": ["type", "string", "relation"]}
            )
            self._schema_cache[model] = fields
        return self._schema_cache[model]

    def search_read(self, model, domain, fields, limit=80, order=None, context=None):
        kwargs = {"fields": fields, "limit": limit, "context": context or {}}
        if order:
            kwargs["order"] = order
        return self._execute_read(model, "search_read", [domain], kwargs)

    def name_search(self, model, name, limit=8, context=None):
        res = self._execute_read(
            model,
            "name_search",
            [],
            {"name": name, "limit": limit, "context": context or {}},
        )
        return [(int(r[0]), str(r[1])) for r in res]

    def message_post(self, model: str, res_id: int, body: str) -> int:
        # zero retry intern (§5); recuperarea = fetch-and-compare în receipts (I6)
        result = self._execute(
            model, "message_post", [[res_id]], {"body": body, "message_type": "comment"}
        )
        if isinstance(result, list):
            result = result[0]
        return int(result)

    def service_partner_id(self) -> int:
        """AIPM_PARTNER_ID — partner_id al utilizatorului de serviciu (descoperit la pornire)."""
        rows = self._execute_read(
            "res.users",
            "search_read",
            [[["login", "=", config.ODOO_RPC_LOGIN]]],
            {"fields": ["partner_id"], "limit": 1},
        )
        if not rows:
            raise AdapterAccessDenied(f"utilizatorul {config.ODOO_RPC_LOGIN} nu există")
        return int(rows[0]["partner_id"][0])
