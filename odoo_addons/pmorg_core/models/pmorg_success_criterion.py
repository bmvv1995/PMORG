from odoo import fields, models


class PmorgSuccessCriterion(models.Model):
    _name = "pmorg.success.criterion"
    _description = "Criteriu de succes PMORG"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="Criteriu", required=True)
    initiative_id = fields.Many2one(
        "pmorg.initiative",
        string="Inițiativă",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="initiative_id.company_id",
        store=True,
    )
    verified = fields.Boolean(string="Verificat", default=False)
    verified_by_id = fields.Many2one(
        "res.users",
        string="Verificat de",
        readonly=True,
        copy=False,
    )
    verified_at = fields.Datetime(string="Verificat la", readonly=True, copy=False)
    evidence_note = fields.Char(string="Notă dovadă")

    def action_mark_verified(self):
        self.write(
            {
                "verified": True,
                "verified_by_id": self.env.user.id,
                "verified_at": fields.Datetime.now(),
            }
        )
