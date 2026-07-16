from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PmorgTaskRun(models.Model):
    """O încercare de execuție a unui task, cu lease. 01-ARCHITECTURE §4.2."""

    _name = "pmorg.task.run"
    _description = "Execuție de task PMORG"
    _order = "id desc"

    task_id = fields.Many2one(
        "project.task", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="task_id.company_id", store=True)
    actor_type = fields.Selection(
        [("agent", "Agent"), ("user", "Utilizator"), ("system", "Sistem")],
        required=True,
        default="agent",
    )
    actor_id = fields.Char(string="Identitatea actorului", required=True)
    started_at = fields.Datetime(required=True, default=fields.Datetime.now)
    ended_at = fields.Datetime()
    outcome = fields.Selection(
        [
            ("running", "În execuție"),
            ("done", "Încheiat"),
            ("failed", "Eșuat"),
            ("needs_review", "Necesită revizuire"),
            ("released", "Eliberat"),
        ],
        default="running",
        required=True,
        index=True,
    )
    failure_reason = fields.Char()
    summary = fields.Text(string="Rezumat")
    lease_token = fields.Char(copy=False)
    lease_expires_at = fields.Datetime(copy=False)

    def is_lease_valid(self, now):
        self.ensure_one()
        return (
            self.outcome == "running"
            and self.lease_expires_at
            and self.lease_expires_at > now
        )


class PmorgTaskEvent(models.Model):
    """Jurnal append-only al tranzițiilor. Nu se editează, nu se șterge."""

    _name = "pmorg.task.event"
    _description = "Eveniment de task PMORG (append-only)"
    _order = "id"

    task_id = fields.Many2one(
        "project.task", required=True, ondelete="restrict", index=True
    )
    run_id = fields.Many2one("pmorg.task.run", ondelete="restrict")
    event_type = fields.Char(required=True, index=True)
    actor_id = fields.Char()
    payload = fields.Json()

    def write(self, vals):
        raise UserError(_("Jurnalul de evenimente este append-only."))

    def unlink(self):
        raise UserError(_("Jurnalul de evenimente este append-only."))


class PmorgOutboxEvent(models.Model):
    """Outbox tranzacțional: scris în aceeași tranzacție cu efectul."""

    _name = "pmorg.outbox.event"
    _description = "Eveniment outbox PMORG"
    _order = "id"

    message_id = fields.Char(required=True, copy=False)
    event_type = fields.Char(required=True, index=True)
    payload = fields.Json()

    _sql_constraints = [
        ("message_id_unique", "unique(message_id)", "message_id trebuie să fie unic."),
    ]


class PmorgCommandInbox(models.Model):
    """Deduplicarea comenzilor externe: (actor, idempotency_key) -> răspuns."""

    _name = "pmorg.command.inbox"
    _description = "Inbox de comenzi PMORG (idempotency)"
    _order = "id"

    actor_id = fields.Char(required=True, index=True)
    idempotency_key = fields.Char(required=True)
    command = fields.Char(required=True)
    response = fields.Json()

    _sql_constraints = [
        (
            "actor_key_unique",
            "unique(actor_id, idempotency_key)",
            "Cheia de idempotency există deja pentru acest actor.",
        ),
    ]
