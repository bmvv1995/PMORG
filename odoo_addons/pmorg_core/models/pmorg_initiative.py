from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PmorgInitiative(models.Model):
    _name = "pmorg.initiative"
    _description = "Inițiativă PMORG"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, create_date desc"

    reference = fields.Char(
        string="Identificator",
        readonly=True,
        copy=False,
        index=True,
    )
    name = fields.Char(string="Nume", required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="Companie",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    owner_identity_id = fields.Many2one(
        "pmorg.identity",
        string="Owner",
        required=True,
        default=lambda self: self._default_owner_identity(),
        tracking=True,
    )
    description = fields.Text(string="Descriere / context")
    objective = fields.Text(string="Obiectiv")
    priority = fields.Selection(
        [
            ("0", "Scăzută"),
            ("1", "Normală"),
            ("2", "Mare"),
            ("3", "Urgentă"),
        ],
        default="1",
        string="Prioritate",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Ciornă"),
            ("clarifying", "Se clarifică"),
            ("planned", "Planificată"),
            ("awaiting_confirmation", "Așteaptă confirmare"),
            ("active", "Activă"),
            ("verifying", "Se verifică"),
            ("closed", "Închisă"),
            ("cancelled", "Anulată"),
        ],
        default="draft",
        string="Stare",
        tracking=True,
        required=True,
    )
    cancel_reason = fields.Text(string="Motivul anulării")
    project_id = fields.Many2one(
        "project.project",
        string="Proiect",
        tracking=True,
    )
    task_ids = fields.One2many(
        "project.task",
        "pmorg_initiative_id",
        string="Taskuri",
    )
    task_count = fields.Integer(
        string="Nr. taskuri",
        compute="_compute_task_count",
    )
    success_criterion_ids = fields.One2many(
        "pmorg.success.criterion",
        "initiative_id",
        string="Criterii de succes",
    )
    active_run_id = fields.Char(string="Run activ (ID extern)")
    state_version = fields.Integer(
        string="Versiune stare",
        default=1,
        readonly=True,
        copy=False,
    )
    next_check_at = fields.Datetime(string="Următoarea verificare")
    last_progress_at = fields.Datetime(string="Ultimul progres")
    followup_count = fields.Integer(string="Nr. follow-up-uri", default=0)
    escalation_level = fields.Integer(string="Nivel escaladare", default=0)
    verification_status = fields.Selection(
        [
            ("not_started", "Neînceput"),
            ("pending", "În așteptare"),
            ("passed", "Trecut"),
            ("failed", "Eșuat"),
        ],
        default="not_started",
        string="Status verificare",
    )
    close_date = fields.Datetime(string="Data închiderii", readonly=True, copy=False)

    def _default_owner_identity(self):
        return self.env["pmorg.identity"].search(
            [
                ("user_id", "=", self.env.uid),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

    @api.depends("task_ids")
    def _compute_task_count(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference"):
                vals["reference"] = (
                    self.env["ir.sequence"].next_by_code("pmorg.initiative") or "/"
                )
        return super().create(vals_list)

    def _check_state_change(self, new_state, vals):
        for rec in self:
            if new_state == "closed":
                if not (vals.get("objective") or rec.objective):
                    raise ValidationError(
                        _("Inițiativa %s nu poate fi închisă fără obiectiv definit.")
                        % rec.display_name
                    )
                unverified = rec.success_criterion_ids.filtered(
                    lambda c: not c.verified
                )
                if unverified:
                    raise ValidationError(
                        _(
                            "Inițiativa %s nu poate fi închisă: "
                            "criterii de succes neverificate: %s."
                        )
                        % (rec.display_name, ", ".join(unverified.mapped("name")))
                    )
            if new_state == "active" and rec.state == "draft":
                raise ValidationError(
                    _("O inițiativă poate deveni activă doar după planificare.")
                )
            if new_state == "cancelled" and not (
                vals.get("cancel_reason") or rec.cancel_reason
            ):
                raise ValidationError(
                    _("Anularea unei inițiative necesită un motiv explicit.")
                )

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pmorg_skip_version"):
            self._check_state_change(vals["state"], vals)
            result = True
            for rec in self:
                rec_vals = dict(vals, state_version=rec.state_version + 1)
                result = (
                    super(
                        PmorgInitiative, rec.with_context(pmorg_skip_version=True)
                    ).write(rec_vals)
                    and result
                )
            return result
        return super().write(vals)

    def action_start_clarification(self):
        return self.write({"state": "clarifying"})

    def action_start_planning(self):
        return self.write({"state": "planned"})

    def action_request_confirmation(self):
        return self.write({"state": "awaiting_confirmation"})

    def action_activate(self):
        return self.write({"state": "active"})

    def action_start_verification(self):
        return self.write({"state": "verifying"})

    def action_close(self):
        return self.write({"state": "closed", "close_date": fields.Datetime.now()})

    def action_cancel(self):
        return self.write({"state": "cancelled"})

    def action_reset_draft(self):
        return self.write({"state": "draft"})
