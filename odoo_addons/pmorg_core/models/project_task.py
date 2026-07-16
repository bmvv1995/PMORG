from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    pmorg_initiative_id = fields.Many2one(
        "pmorg.initiative",
        string="Inițiativă PMORG",
        tracking=True,
        index=True,
    )
    pmorg_task_type = fields.Selection(
        [
            ("execution", "Execuție"),
            ("clarification", "Clarificare"),
            ("investigation", "Investigație"),
            ("planning", "Planificare"),
            ("followup", "Follow-up"),
            ("confirmation", "Confirmare"),
            ("monitoring", "Monitorizare"),
            ("escalation", "Escaladare"),
            ("verification", "Verificare"),
        ],
        string="Tip task PMORG",
        tracking=True,
    )
    execution_mode = fields.Selection(
        [
            ("human", "Uman"),
            ("agent", "Agent"),
            ("hybrid", "Hibrid"),
            ("monitor", "Monitor"),
        ],
        default="human",
        string="Mod execuție",
        tracking=True,
    )
    expected_outcome = fields.Text(string="Rezultat așteptat")
    completion_criteria = fields.Text(string="Criterii de completare")
    orchestration_state = fields.Selection(
        [
            ("not_managed", "Ne-gestionat"),
            ("ready", "Pregătit"),
            ("claimed", "Revendicat"),
            ("running", "În execuție"),
            ("waiting_response", "Așteaptă răspuns"),
            ("waiting_approval", "Așteaptă aprobare"),
            ("scheduled", "Programat"),
            ("blocked", "Blocat"),
            ("review", "În revizuire"),
            ("failed", "Eșuat"),
            ("completed", "Finalizat"),
            ("cancelled", "Anulat"),
        ],
        default="not_managed",
        string="Stare orchestrare",
        tracking=True,
    )
    next_check_at = fields.Datetime(string="Următoarea verificare")
    awaiting_response_from = fields.Many2one(
        "pmorg.identity",
        string="Așteaptă răspuns de la",
    )
    awaiting_since = fields.Datetime(string="Așteaptă de la")
    last_progress_at = fields.Datetime(string="Ultimul progres")
    last_intervention_at = fields.Datetime(string="Ultima intervenție")
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
    active_run_id = fields.Char(string="Run activ (ID)")
    state_version = fields.Integer(
        string="Versiune stare", default=1, readonly=True, copy=False
    )
    participant_ids = fields.Many2many(
        "pmorg.identity",
        "pmorg_task_participant_rel",
        "task_id",
        "identity_id",
        string="Participanți",
    )
    anchor_ids = fields.One2many(
        "pmorg.anchor",
        "task_id",
        string="Ancore",
    )
