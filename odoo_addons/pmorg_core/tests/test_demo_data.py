from odoo.tests.common import TransactionCase


class TestDemoData(TransactionCase):
    """Verifică fixture-urile ORG-MIN (rulează doar când demo e încărcat)."""

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

        self.assertEqual(company.name, "Atelier Minimal Test SRL")
        self.assertEqual(init.company_id, company)
        self.assertEqual(init.project_id, self._demo("pmorg_demo_project"))
        self.assertEqual(init.task_ids, clarify | action)
        self.assertEqual(clarify.execution_mode, "agent")
        self.assertEqual(clarify.pmorg_task_type, "clarification")
        self.assertEqual(action.execution_mode, "human")

    def test_demo_identities_canonical(self):
        ana = self._demo("pmorg_demo_identity_ana")
        paul = self._demo("pmorg_demo_identity_paul")
        victor = self._demo("pmorg_demo_identity_victor")
        agent = self._demo("pmorg_demo_identity_agent")
        init = self._demo("pmorg_demo_initiative")

        # Ownerul e referit exclusiv prin pmorg.identity (ADR-014).
        self.assertEqual(init.owner_identity_id, ana)
        # Ana acționează în Odoo => are user consistent cu partenerul.
        self.assertTrue(ana.user_id)
        self.assertEqual(ana.user_id.partner_id, ana.partner_id)
        # Validatorul și participantul nu au nevoie de user.
        self.assertFalse(paul.user_id)
        self.assertFalse(victor.user_id)
        self.assertEqual(agent.identity_kind, "agent")

    def test_demo_participant_via_identity(self):
        clarify = self._demo("pmorg_demo_task_clarify")
        victor = self._demo("pmorg_demo_identity_victor")
        init = self._demo("pmorg_demo_initiative")
        self.assertIn(victor, clarify.participant_ids)
        subject = clarify.anchor_ids.filtered(lambda a: a.role == "subject")
        self.assertEqual(len(subject), 1)
        self.assertEqual(subject.model_name, "pmorg.initiative")
        self.assertEqual(subject.res_id, init.id)

    def test_demo_no_employees_no_real_identifiers(self):
        # Profilul minimal nu are angajați — modelul hr.employee nici nu
        # trebuie să existe în registry (baza nu instalează hr).
        self.assertNotIn("hr.employee", self.env.registry)
        for xmlid in (
            "pmorg_demo_partner_ana",
            "pmorg_demo_partner_paul",
            "pmorg_demo_partner_victor",
        ):
            partner = self._demo(xmlid)
            self.assertTrue(partner.email.endswith(".example"))
            self.assertFalse(partner.phone)
