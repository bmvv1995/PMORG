from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestPmorgTask(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Proiect test"})
        cls.task = cls.env["project.task"].create(
            {"name": "Task test", "project_id": cls.project.id}
        )

    def test_execution_mode_validated(self):
        for mode in ("human", "agent", "hybrid", "monitor"):
            self.task.execution_mode = mode
        with self.assertRaises(ValueError):
            self.task.execution_mode = "alien"

    def test_task_type_validated(self):
        with self.assertRaises(ValueError):
            self.task.pmorg_task_type = "inexistent"

    def test_default_orchestration_state(self):
        self.assertEqual(self.task.orchestration_state, "not_managed")
        self.assertEqual(self.task.state_version, 1)

    def test_anchor_single_subject(self):
        Anchor = self.env["pmorg.anchor"]
        Anchor.create(
            {
                "task_id": self.task.id,
                "model_name": "project.project",
                "res_id": self.project.id,
                "role": "subject",
            }
        )
        with self.assertRaises(ValidationError):
            Anchor.create(
                {
                    "task_id": self.task.id,
                    "model_name": "res.partner",
                    "res_id": 1,
                    "role": "subject",
                }
            )

    def test_anchor_mentions_multiple_allowed(self):
        Anchor = self.env["pmorg.anchor"]
        for res_id in (1, 2):
            Anchor.create(
                {
                    "task_id": self.task.id,
                    "model_name": "res.partner",
                    "res_id": res_id,
                    "role": "mentions",
                }
            )
        self.assertEqual(len(self.task.anchor_ids), 2)
