import uuid

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user

NOW = "2026-07-16 10:00:00"


class TestTrustedClock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api = cls.env["pmorg.orchestrator.api"]
        cls.env["pmorg.identity"].create({
            "partner_id": cls.env.user.partner_id.id, "user_id": cls.env.uid,
        })
        cls.project = cls.env["project.project"].create({"name": "Proiect tick"})
        cls.init = cls.env["pmorg.initiative"].create(
            {"name": "Inițiativă tick", "project_id": cls.project.id}
        )
        cls.task = cls.env["project.task"].create({
            "name": "Task tick", "project_id": cls.project.id,
            "pmorg_initiative_id": cls.init.id,
            "orchestration_state": "ready",
        })

    def _call(self, command, params, now=NOW):
        return self.api.api_call(command, {
            "schema_version": "1.0", "message_id": str(uuid.uuid4()),
            "correlation_id": "tick", "causation_id": None,
            "idempotency_key": str(uuid.uuid4()),
            "actor": {"type": "agent", "id": "runner-tick"},
            "occurred_at": now, "params": params,
        })

    def _set_mode(self, mode):
        self.env["ir.config_parameter"].sudo().set_param(
            "pmorg.clock_mode", mode)

    def test_register_tick_requires_system(self):
        user = new_test_user(self.env, login="tick_user")
        with self.assertRaises(AccessError):
            self.env["pmorg.clock.tick"].with_user(user).create({
                "tick_id": "t-x", "seq": 99, "sim_time": NOW})

    def test_tick_mode_enforced_and_resolves(self):
        self._set_mode("tick")
        self.addCleanup(self._set_mode, "client")

        refused = self._call("claim_task", {"task_id": self.task.id})
        self.assertEqual(refused["error"]["code"], "E_SCHEMA")

        unknown = self._call("claim_task", {"task_id": self.task.id,
                                            "tick_id": "fals"})
        self.assertEqual(unknown["error"]["code"], "E_AUTH")

        self._call("register_tick", {"tick_id": "t-1", "seq": 1,
                                     "sim_time": "2026-07-20 09:00:00"})
        claim = self._call("claim_task", {"task_id": self.task.id,
                                          "tick_id": "t-1"})
        self.assertEqual(claim["status"], "ok", claim)
        run = self.env["pmorg.task.run"].browse(claim["result"]["run_id"])
        self.assertEqual(str(run.started_at), "2026-07-20 09:00:00")

    def test_ticks_immutable(self):
        self._call("register_tick", {"tick_id": "t-2", "seq": 2,
                                     "sim_time": NOW})
        tick = self.env["pmorg.clock.tick"].search([("tick_id", "=", "t-2")])
        with self.assertRaises(AccessError):
            tick.sim_time = "2027-01-01 00:00:00"
        with self.assertRaises(AccessError):
            tick.unlink()

    def test_client_mode_still_accepts_now(self):
        self._set_mode("client")
        listing = self._call("list_due_work", {"now": NOW})
        self.assertEqual(listing["status"], "ok")
