from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PmorgIdentity(models.Model):
    """Identitatea canonică PMORG (ADR-014).

    Ownerii, validatorii, participanții, agenții și sistemele sunt referite
    în nucleu exclusiv prin acest model. Partner obligatoriu, user opțional;
    fără câmpuri alternative către employee.
    """

    _name = "pmorg.identity"
    _description = "Identitate PMORG"
    _order = "id"

    company_id = fields.Many2one(
        "res.company",
        string="Companie",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partener",
        required=True,
        ondelete="restrict",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Utilizator Odoo",
        ondelete="restrict",
    )
    identity_kind = fields.Selection(
        [
            ("human", "Om"),
            ("agent", "Agent"),
            ("system", "Sistem"),
        ],
        string="Tip identitate",
        required=True,
        default="human",
    )
    name = fields.Char(related="partner_id.name", store=True)
    active = fields.Boolean(default=True)

    _company_partner_unique = models.Constraint(
        "UNIQUE (company_id, partner_id)",
        "Există deja o identitate pentru acest partener în această companie.",
    )

    @api.constrains("user_id", "partner_id")
    def _check_user_partner_consistency(self):
        for rec in self.filtered("user_id"):
            if rec.user_id.partner_id != rec.partner_id:
                raise ValidationError(
                    _(
                        "Utilizatorul %(user)s are partenerul %(user_partner)s, "
                        "dar identitatea referă partenerul %(partner)s."
                    )
                    % {
                        "user": rec.user_id.login,
                        "user_partner": rec.user_id.partner_id.display_name,
                        "partner": rec.partner_id.display_name,
                    }
                )
