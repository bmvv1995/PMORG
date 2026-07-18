import uuid

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

NOW = "2026-07-16 10:00:00"


class TestProvenanceD1(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api = cls.env["pmorg.orchestrator.api"]
        cls.identity = cls.env["pmorg.identity"].create({
            "partner_id": cls.env.user.partner_id.id,
            "user_id": cls.env.uid,
        })
        cls.project = cls.env["project.project"].create({"name": "Proiect D1"})
        cls.init = cls.env["pmorg.initiative"].create({
            "name": "Inițiativă D1", "project_id": cls.project.id,
        })
        # închide ciclul de tracking al creării: scrierile din teste vor fi
        # cicluri noi, deci trackuite (creare+scriere în același ciclu = suprimat)
        cls.env.flush_all()
        cls.env.cr.precommit.run()

    def _call(self, command, params):
        return self.api.api_call(command, {
            "schema_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "correlation_id": "d1",
            "causation_id": None,
            "idempotency_key": str(uuid.uuid4()),
            "actor": {"type": "agent", "id": "detector-d1"},
            "occurred_at": NOW,
            "params": params,
        })

    def test_materiality_seeded(self):
        rules = self.env["pmorg.materiality.rule"].search([])
        pairs = {(r.model_name, r.field_name) for r in rules}
        self.assertIn(("pmorg.initiative", "state"), pairs)
        self.assertIn(("project.task", "date_deadline"), pairs)

    def test_material_change_detected_and_gap_lifecycle(self):
        self.init.action_start_clarification()
        self.env.flush_all()
        self.env.cr.precommit.run()  # tracking-ul se materializează la precommit
        resp = self._call("list_material_changes", {"since": NOW})
        changes = [c for c in resp["result"]["changes"]
                   if c["model_name"] == "pmorg.initiative"
                   and c["res_id"] == self.init.id
                   and c["field_name"] == "state"]
        self.assertTrue(changes, resp["result"])
        change = changes[0]

        gap = self._call("record_provenance_gap", dict(
            change, summary="stare schimbată fără decizie"))
        self.assertEqual(gap["result"]["status"], "open")
        self.assertFalse(gap["result"]["replayed"])
        again = self._call("record_provenance_gap", dict(
            change, summary="dublură"))
        self.assertTrue(again["result"]["replayed"])
        self.assertEqual(again["result"]["gap_id"], gap["result"]["gap_id"])

        refuse = self._call("resolve_gap", {
            "gap_id": gap["result"]["gap_id"], "resolution": "explained"})
        self.assertEqual(refuse["error"]["code"], "E_CRITERIA")

        done = self._call("resolve_gap", {
            "gap_id": gap["result"]["gap_id"], "resolution": "explained",
            "memory_ref": "mem://ns/claim/42",
            "identity_id": self.identity.id})
        self.assertEqual(done["result"]["status"], "explained")
        record = self.env["pmorg.provenance.gap"].browse(
            gap["result"]["gap_id"])
        self.assertEqual(record.explained_memory_ref, "mem://ns/claim/42")
        self.assertEqual(record.resolved_by_identity_id, self.identity)

        closed = self._call("resolve_gap", {
            "gap_id": gap["result"]["gap_id"], "resolution": "dismissed"})
        self.assertEqual(closed["error"]["code"], "E_STATE")

    def test_gap_model_resolution_guard(self):
        gap = self.env["pmorg.provenance.gap"].create({
            "model_name": "pmorg.initiative", "res_id": self.init.id,
            "field_name": "state", "tracking_message_id": 1,
            "summary": "test",
        })
        with self.assertRaises(ValidationError):
            gap.action_resolve("explained")
