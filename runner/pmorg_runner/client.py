"""Client XML-RPC pentru contractul pmorg.orchestrator.api (06-CONTRACTS v1.0).

Runnerul este un client pur al contractului: nu conține reguli de business.
"""

import uuid
import xmlrpc.client


class OdooApiClient:
    def __init__(self, url, db, login, password, actor_id="runner-mvp"):
        self.url = url
        self.db = db
        self.password = password
        self.actor_id = actor_id
        common = xmlrpc.client.ServerProxy(
            f"{url}/xmlrpc/2/common", allow_none=True
        )
        self.uid = common.authenticate(db, login, password, {})
        if not self.uid:
            raise RuntimeError("Autentificare eșuată la Odoo.")
        self.models = xmlrpc.client.ServerProxy(
            f"{url}/xmlrpc/2/object", allow_none=True
        )
        self._idem_counter = 0
        # nonce per proces: cheile rămân stabile ÎN interiorul unei rulări
        # (replay intenționat), dar nu se ciocnesc între rulări pe aceeași bază
        self._run_nonce = uuid.uuid4().hex[:8]

    def next_key(self, label):
        self._idem_counter += 1
        return f"{self.actor_id}:{self._run_nonce}:{label}:{self._idem_counter}"

    def call(self, command, params, now, key=None, correlation_id=None):
        payload = {
            "schema_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "correlation_id": correlation_id or "smoke-XNX-001",
            "causation_id": None,
            "idempotency_key": key or self.next_key(command),
            "actor": {"type": "agent", "id": self.actor_id},
            "occurred_at": now,
            "params": params,
        }
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            "pmorg.orchestrator.api",
            "api_call",
            [command, payload],
        )

    def execute(self, model, method, *args, **kwargs):
        """Acces direct de fixture (rolul omului în scenariu), nu al runtime-ului."""
        return self.models.execute_kw(
            self.db, self.uid, self.password, model, method, list(args), kwargs
        )
