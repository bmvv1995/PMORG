from psycopg2.errors import UniqueViolation

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestIdentity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Persoană test"})

    def test_identity_minimal(self):
        identity = self.env["pmorg.identity"].create(
            {"partner_id": self.partner.id}
        )
        self.assertEqual(identity.identity_kind, "human")
        self.assertEqual(identity.company_id, self.env.company)
        self.assertEqual(identity.name, "Persoană test")
        self.assertFalse(identity.user_id)

    @mute_logger("odoo.sql_db")
    def test_identity_unique_per_company_partner(self):
        self.env["pmorg.identity"].create({"partner_id": self.partner.id})
        with self.assertRaises(UniqueViolation):
            with self.env.cr.savepoint():
                self.env["pmorg.identity"].create(
                    {"partner_id": self.partner.id}
                )
                self.env.flush_all()

    def test_identity_user_partner_consistency(self):
        with self.assertRaises(ValidationError):
            self.env["pmorg.identity"].create(
                {
                    "partner_id": self.partner.id,
                    "user_id": self.env.uid,
                }
            )
