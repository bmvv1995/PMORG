from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user


class TestAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="pmorg_basic_user")

    def test_internal_user_crud_no_unlink(self):
        Initiative = self.env["pmorg.initiative"].with_user(self.user)
        init = Initiative.create({"name": "Inițiativă user"})
        self.assertTrue(init.reference)
        init.write({"description": "editat"})
        records = Initiative.search([("id", "=", init.id)])
        self.assertEqual(records, init)
        with self.assertRaises(AccessError):
            init.unlink()

    def test_admin_can_unlink(self):
        init = self.env["pmorg.initiative"].create({"name": "De șters"})
        init.unlink()
        self.assertFalse(init.exists())
