from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestInitiative(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Proiect test"})

    def _make(self, **vals):
        base = {"name": "Inițiativă test", "project_id": self.project.id}
        base.update(vals)
        return self.env["pmorg.initiative"].create(base)

    def test_create_links_project_and_gets_reference(self):
        init = self._make()
        self.assertEqual(init.project_id, self.project)
        self.assertTrue(init.reference.startswith("PMORG-"))
        self.assertEqual(init.state, "draft")
        self.assertEqual(init.state_version, 1)
        self.assertEqual(init.company_id, self.env.company)

    def test_task_links_to_initiative(self):
        init = self._make()
        task = self.env["project.task"].create(
            {
                "name": "Task test",
                "project_id": self.project.id,
                "pmorg_initiative_id": init.id,
                "pmorg_task_type": "clarification",
                "execution_mode": "agent",
            }
        )
        self.assertIn(task, init.task_ids)
        self.assertEqual(init.task_count, 1)

    def test_close_without_objective_refused(self):
        init = self._make(objective=False)
        init.state = "verifying"
        with self.assertRaises(ValidationError):
            init.action_close()

    def test_close_with_unverified_criteria_refused(self):
        init = self._make(objective="Obiectiv")
        self.env["pmorg.success.criterion"].create(
            {"name": "Criteriu", "initiative_id": init.id}
        )
        init.state = "verifying"
        with self.assertRaises(ValidationError):
            init.action_close()
        init.success_criterion_ids.action_mark_verified()
        init.action_close()
        self.assertEqual(init.state, "closed")
        self.assertTrue(init.close_date)

    def test_activate_from_draft_refused(self):
        init = self._make()
        with self.assertRaises(ValidationError):
            init.action_activate()

    def test_cancel_requires_reason(self):
        init = self._make()
        with self.assertRaises(ValidationError):
            init.action_cancel()
        init.write({"state": "cancelled", "cancel_reason": "Motiv de test"})
        self.assertEqual(init.state, "cancelled")

    def test_state_version_increments_per_record(self):
        a = self._make(name="A")
        b = self._make(name="B")
        b.action_start_clarification()
        self.assertEqual(b.state_version, 2)
        both = a | b
        both.write({"state": "clarifying"})
        self.assertEqual(a.state_version, 2)
        self.assertEqual(b.state_version, 3)
