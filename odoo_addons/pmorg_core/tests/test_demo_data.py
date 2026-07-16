from odoo.tests.common import TransactionCase


class TestDemoData(TransactionCase):
    """Verifică fixture-urile sintetice (rulează doar când demo e încărcat)."""

    def _demo(self, xmlid):
        return self.env.ref(f"pmorg_core.{xmlid}", raise_if_not_found=False)

    def setUp(self):
        super().setUp()
        if not self._demo("pmorg_demo_initiative"):
            self.skipTest("Datele demo nu sunt încărcate în această bază.")

    def test_demo_world_coherent(self):
        company = self._demo("pmorg_demo_company")
        init = self._demo("pmorg_demo_initiative")
        clarify = self._demo("pmorg_demo_task_clarify")
        action = self._demo("pmorg_demo_task_action")

        self.assertEqual(company.name, "Delta Distribution Test SRL")
        self.assertEqual(init.company_id, company)
        self.assertEqual(init.project_id, self._demo("pmorg_demo_project"))
        self.assertEqual(init.task_ids, clarify | action)
        self.assertEqual(clarify.execution_mode, "agent")
        self.assertEqual(clarify.pmorg_task_type, "clarification")
        self.assertEqual(action.execution_mode, "human")

    def test_demo_management_chain(self):
        mara = self._demo("pmorg_demo_employee_mara")
        andrei = self._demo("pmorg_demo_employee_andrei")
        mihai = self._demo("pmorg_demo_employee_mihai")
        self.assertEqual(mihai.parent_id, andrei)
        self.assertEqual(andrei.parent_id, mara)

    def test_demo_anchor_and_participant(self):
        clarify = self._demo("pmorg_demo_task_clarify")
        init = self._demo("pmorg_demo_initiative")
        mihai_p = self._demo("pmorg_demo_partner_mihai")
        subject = clarify.anchor_ids.filtered(lambda a: a.role == "subject")
        self.assertEqual(len(subject), 1)
        self.assertEqual(subject.model_name, "pmorg.initiative")
        self.assertEqual(subject.res_id, init.id)
        self.assertIn(mihai_p, clarify.participant_ids)

    def test_demo_no_real_identifiers(self):
        for xmlid in (
            "pmorg_demo_partner_mara",
            "pmorg_demo_partner_andrei",
            "pmorg_demo_partner_mihai",
        ):
            partner = self._demo(xmlid)
            self.assertTrue(partner.email.endswith(".example"))
            self.assertFalse(partner.phone)
