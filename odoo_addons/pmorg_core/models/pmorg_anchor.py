from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PmorgAnchor(models.Model):
    """Ancoră minimă către o înregistrare Odoo.

    Prima felie: doar identitatea țintei și rolul relației. Extensiile MVP
    (instance UUID, versiunea schemei, write_date observat) se adaugă la
    înghețarea contractelor, conform 01-ARCHITECTURE §6.
    """

    _name = "pmorg.anchor"
    _description = "Ancoră PMORG către o înregistrare Odoo"
    _order = "id"

    company_id = fields.Many2one(
        "res.company",
        string="Companie",
        required=True,
        default=lambda self: self.env.company,
    )
    task_id = fields.Many2one(
        "project.task",
        string="Task",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model_name = fields.Char(string="Model Odoo", required=True)
    res_id = fields.Integer(string="ID înregistrare", required=True)
    role = fields.Selection(
        [
            ("subject", "Subiect"),
            ("participant", "Participant"),
            ("mentions", "Menționat"),
        ],
        string="Rol",
        required=True,
        default="subject",
    )
    note = fields.Char(string="Notă")
    name = fields.Char(compute="_compute_name")

    _anchor_unique = models.Constraint(
        "UNIQUE (task_id, model_name, res_id, role)",
        "Ancora există deja pe acest task cu același rol.",
    )

    @api.depends("model_name", "res_id", "role")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.model_name},{rec.res_id} ({rec.role})"

    @api.constrains("model_name")
    def _check_model_registered(self):
        Registry = self.env["pmorg.anchor.type"]
        for rec in self:
            if not Registry.search_count(
                [("model_name", "=", rec.model_name), ("active", "=", True)]
            ):
                raise ValidationError(
                    _(
                        "Modelul %s nu are tip de ancoră în registry "
                        "(ADR-002: lume închisă, fail-closed)."
                    )
                    % rec.model_name
                )

    @api.constrains("role", "task_id")
    def _check_single_subject(self):
        for rec in self.filtered(lambda a: a.role == "subject"):
            others = self.search_count(
                [
                    ("task_id", "=", rec.task_id.id),
                    ("role", "=", "subject"),
                    ("id", "!=", rec.id),
                ]
            )
            if others:
                raise ValidationError(
                    _("Un task poate avea o singură ancoră cu rol de subiect.")
                )
