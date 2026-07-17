from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class PmorgClockTick(models.Model):
    """Ceasul trusted al sandboxului (ADR-017, contract 2.0-draft).

    Harness-ul (identitate de sistem) înregistrează tick-uri: capabilități
    opace tick_id -> sim_time. Runtime-ul le PREZINTĂ, nu le creează: un
    tick_id neînregistrat nu rezolvă timpul. În modul 'tick'
    (ir.config_parameter pmorg.clock_mode), comenzile mutante refuză `now`
    furnizat de client.
    """

    _name = "pmorg.clock.tick"
    _description = "Tick al ceasului trusted PMORG"
    _order = "seq"

    tick_id = fields.Char(required=True, index=True)
    seq = fields.Integer(required=True)
    sim_time = fields.Datetime(required=True)

    _tick_unique = models.Constraint("UNIQUE (tick_id)", "tick_id duplicat.")
    _seq_unique = models.Constraint("UNIQUE (seq)", "seq duplicat.")

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(
                _("Doar harness-ul (sistem) poate înregistra tick-uri.")
            )
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_("Tick-urile sunt imuabile."))

    def unlink(self):
        raise AccessError(_("Tick-urile sunt imuabile."))
