import uuid

from odoo.tests.common import TransactionCase

NOW = "2026-07-16 10:00:00"
LATER = "2026-07-16 12:00:00"


class TestOrchestratorApi(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api = cls.env["pmorg.orchestrator.api"]
        cls.identity = cls.env["pmorg.identity"].create(
            {
                "partner_id": cls.env.user.partner_id.id,
                "user_id": cls.env.uid,
                "identity_kind": "human",
            }
        )
        cls.project = cls.env["project.project"].create({"name": "Proiect API"})
        cls.initiative = cls.env["pmorg.initiative"].create(
            {"name": "Inițiativă API", "project_id": cls.project.id}
        )
        cls.task = cls.env["project.task"].create(
            {
                "name": "Task API",
                "project_id": cls.project.id,
                "pmorg_initiative_id": cls.initiative.id,
                "pmorg_task_type": "clarification",
                "execution_mode": "agent",
            }
        )

    def _payload(self, params=None, actor="runner-1", key=None, now=NOW):
        return {
            "schema_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "correlation_id": "corr-1",
            "causation_id": None,
            "idempotency_key": key or str(uuid.uuid4()),
            "actor": {"type": "agent", "id": actor},
            "occurred_at": now,
            "params": params or {},
        }

    def _call(self, command, params=None, **kw):
        return self.api.api_call(command, self._payload(params, **kw))

    def _claimed(self):
        self._call("mark_managed", {"task_id": self.task.id})
        resp = self._call("claim_task", {"task_id": self.task.id})
        self.assertEqual(resp["status"], "ok", resp)
        return resp["result"]

    # ------------------------------------------------------------- anvelopă

    def test_envelope_missing_fields(self):
        resp = self.api.api_call("mark_managed", {"schema_version": "1.0"})
        self.assertEqual(resp["status"], "error")
        self.assertEqual(resp["error"]["code"], "E_SCHEMA")

    def test_envelope_wrong_major_version(self):
        payload = self._payload({"task_id": self.task.id})
        payload["schema_version"] = "2.0"
        resp = self.api.api_call("mark_managed", payload)
        self.assertEqual(resp["error"]["code"], "E_SCHEMA")

    def test_unknown_command(self):
        resp = self._call("nu_exista", {})
        self.assertEqual(resp["error"]["code"], "E_SCHEMA")

    # ---------------------------------------------------------------- claim

    def test_claim_lifecycle(self):
        claim = self._claimed()
        self.assertEqual(self.task.orchestration_state, "claimed")
        self.assertTrue(claim["lease_token"])

        run_ref = {
            "task_id": self.task.id,
            "run_id": claim["run_id"],
            "lease_token": claim["lease_token"],
        }
        resp = self._call("record_progress", dict(run_ref, note="am contactat"))
        self.assertEqual(resp["status"], "ok", resp)
        self.assertEqual(self.task.orchestration_state, "running")

        resp = self._call(
            "record_waiting_response",
            dict(run_ref, awaiting_identity_id=self.identity.id),
        )
        self.assertEqual(self.task.orchestration_state, "waiting_response")
        self.assertEqual(self.task.awaiting_response_from, self.identity)

        resp = self._call("record_progress", dict(run_ref, note="a răspuns"))
        self.assertEqual(self.task.orchestration_state, "running")

        resp = self._call(
            "complete_run", dict(run_ref, outcome="done", summary="clarificat")
        )
        self.assertEqual(resp["status"], "ok", resp)
        self.assertEqual(self.task.orchestration_state, "completed")
        self.assertFalse(self.task.active_run_id)

    def test_claim_not_managed_refused(self):
        resp = self._call("claim_task", {"task_id": self.task.id})
        self.assertEqual(resp["error"]["code"], "E_STATE")

    def test_double_claim_refused(self):
        self._claimed()
        resp = self._call("claim_task", {"task_id": self.task.id}, actor="runner-2")
        self.assertEqual(resp["error"]["code"], "E_LEASE_HELD")

    def test_claim_replay_returns_same_result(self):
        self._call("mark_managed", {"task_id": self.task.id})
        key = "claim-idem-1"
        first = self._call("claim_task", {"task_id": self.task.id}, key=key)
        again = self._call("claim_task", {"task_id": self.task.id}, key=key)
        self.assertEqual(again["status"], "replay")
        self.assertEqual(
            again["result"]["run_id"], first["result"]["run_id"]
        )
        self.assertEqual(
            self.env["pmorg.task.run"].search_count(
                [("task_id", "=", self.task.id)]
            ),
            1,
        )

    def test_claim_version_conflict(self):
        self._call("mark_managed", {"task_id": self.task.id})
        resp = self._call(
            "claim_task", {"task_id": self.task.id, "expected_version": 99}
        )
        self.assertEqual(resp["error"]["code"], "E_VERSION")

    # ------------------------------------------------------------ lease/timp

    def test_lease_expiry_and_late_result(self):
        claim = self._claimed()
        run_ref = {
            "task_id": self.task.id,
            "run_id": claim["run_id"],
            "lease_token": claim["lease_token"],
        }
        resp = self._call("reclaim_expired", {"now": LATER}, now=LATER)
        self.assertIn(claim["run_id"], resp["result"]["reclaimed_run_ids"])
        self.assertEqual(self.task.orchestration_state, "ready")

        late = self._call(
            "complete_run",
            dict(run_ref, outcome="done", summary="târziu", now=LATER),
            now=LATER,
        )
        self.assertEqual(late["error"]["code"], "E_LEASE")

    def test_heartbeat_extends_only_owner(self):
        claim = self._claimed()
        resp = self._call(
            "heartbeat",
            {
                "task_id": self.task.id,
                "run_id": claim["run_id"],
                "lease_token": "token-fals",
            },
        )
        self.assertEqual(resp["error"]["code"], "E_LEASE")
        resp = self._call(
            "heartbeat",
            {
                "task_id": self.task.id,
                "run_id": claim["run_id"],
                "lease_token": claim["lease_token"],
                "extend_seconds": 600,
            },
        )
        self.assertEqual(resp["status"], "ok")

    def test_schedule_and_due_claim(self):
        claim = self._claimed()
        run_ref = {
            "task_id": self.task.id,
            "run_id": claim["run_id"],
            "lease_token": claim["lease_token"],
        }
        resp = self._call(
            "schedule_next_check",
            dict(run_ref, next_check_at="2026-07-16 11:00:00", reason="revin"),
        )
        self.assertEqual(self.task.orchestration_state, "scheduled")

        early = self._call("claim_task", {"task_id": self.task.id})
        self.assertEqual(early["error"]["code"], "E_NOT_DUE")

        due = self._call("claim_task", {"task_id": self.task.id, "now": LATER},
                         now=LATER)
        self.assertEqual(due["status"], "ok", due)

    # ----------------------------------------------------------- list & rest

    def test_list_due_work_scheduled_due(self):
        self._call("mark_managed", {"task_id": self.task.id})
        listing = self._call("list_due_work", {"now": NOW})
        ids = [t["task_id"] for t in listing["result"]["tasks"]]
        self.assertIn(self.task.id, ids)

    def test_complete_with_criteria_requires_evidence(self):
        self.task.completion_criteria = "Concluzie confirmată cu dovadă"
        claim = self._claimed()
        run_ref = {
            "task_id": self.task.id,
            "run_id": claim["run_id"],
            "lease_token": claim["lease_token"],
        }
        self._call("record_progress", dict(run_ref, note="lucru"))
        resp = self._call(
            "complete_run", dict(run_ref, outcome="done", summary="gata")
        )
        self.assertEqual(resp["error"]["code"], "E_CRITERIA")
        resp = self._call(
            "complete_run",
            dict(run_ref, outcome="done", summary="gata",
                 evidence_refs=["mem://evidence/1"]),
        )
        self.assertEqual(resp["status"], "ok", resp)

    def test_propose_task(self):
        resp = self._call(
            "propose_task",
            {
                "initiative_id": self.initiative.id,
                "name": "Task propus",
                "pmorg_task_type": "followup",
                "execution_mode": "agent",
            },
        )
        task = self.env["project.task"].browse(resp["result"]["task_id"])
        self.assertEqual(task.orchestration_state, "ready")
        self.assertEqual(task.pmorg_initiative_id, self.initiative)

    def test_execute_authorized_command_fail_closed(self):
        resp = self._call("execute_authorized_command", {"command": "orice"})
        self.assertEqual(resp["error"]["code"], "E_AUTONOMY")

    def test_events_append_only_and_outbox(self):
        self._claimed()
        events = self.env["pmorg.task.event"].search(
            [("task_id", "=", self.task.id)]
        )
        self.assertTrue(events)
        with self.assertRaises(Exception):
            events[0].event_type = "alterat"
        with self.assertRaises(Exception):
            events[0].unlink()
        outbox = self.env["pmorg.outbox.event"].search_count(
            [("event_type", "in", ("task.ready", "task.claimed"))]
        )
        self.assertGreaterEqual(outbox, 2)

    def test_outbox_listing_after_id(self):
        self._claimed()
        listing = self._call("list_outbox", {"after_id": 0})
        self.assertTrue(listing["result"]["events"])
        last_id = listing["result"]["events"][-1]["id"]
        empty = self._call("list_outbox", {"after_id": last_id})
        self.assertFalse(empty["result"]["events"])
