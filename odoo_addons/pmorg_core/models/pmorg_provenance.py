from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PmorgMaterialityRule(models.Model):
    """Registrul guvernat de materialitate (08-MEMORY-CHANNELS §2.4).

    Ce câmpuri poartă decizii. Seedat prin date, calibrat prin feedback uman —
    niciodată ghicit la runtime.
    """

    _name = "pmorg.materiality.rule"
    _description = "Regulă de materialitate PMORG"
    _order = "model_name, field_name"

    model_name = fields.Char(required=True)
    field_name = fields.Char(required=True)
    pack = fields.Char(required=True, default="pmorg_core")
    active = fields.Boolean(default=True)

    _model_field_unique = models.Constraint(
        "UNIQUE (model_name, field_name)", "Regula există deja."
    )


class PmorgProvenanceGap(models.Model):
    """Un gol de proveniență: efect formal fără cauză consemnată (D1–D5).

    Suspiciune cu fereastră declarată, nu verdict. Răspunsul omului îl
    închide și devine memorie (bucla din 08 §2.3).
    """

    _name = "pmorg.provenance.gap"
    _description = "Gol de proveniență PMORG"
    _order = "id desc"

    gap_class = fields.Selection(
        [("d1", "Efect fără cauză"), ("d2", "Angajament rezolvat în întuneric"),
         ("d3", "Referință-fantomă"), ("d4", "Inițiativă fără urmă"),
         ("d5", "Actor întunecat")],
        required=True, default="d1",
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    model_name = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    field_name = fields.Char()
    tracking_message_id = fields.Integer(
        help="mail.message-ul cu tracking care dovedește efectul."
    )
    summary = fields.Char(required=True)
    window_hours = fields.Integer(default=72)
    status = fields.Selection(
        [("open", "Deschis"), ("explained", "Explicat"),
         ("dismissed", "Respins (trivial)")],
        default="open", required=True, index=True,
    )
    explained_memory_ref = fields.Char(
        help="Referința claim-ului de memorie care a închis golul."
    )
    resolved_by_identity_id = fields.Many2one("pmorg.identity")
    resolved_at = fields.Datetime(readonly=True)

    _effect_unique = models.Constraint(
        "UNIQUE (model_name, res_id, field_name, tracking_message_id)",
        "Golul pentru acest efect există deja.",
    )

    def action_resolve(self, resolution, memory_ref=False, identity_id=False):
        for gap in self:
            if gap.status != "open":
                raise ValidationError(_("Golul nu mai e deschis."))
            if resolution == "explained" and not memory_ref:
                raise ValidationError(
                    _("Explicarea cere referința de memorie a răspunsului.")
                )
            gap.write({
                "status": resolution,
                "explained_memory_ref": memory_ref,
                "resolved_by_identity_id": identity_id,
                "resolved_at": fields.Datetime.now(),
            })
        return True
