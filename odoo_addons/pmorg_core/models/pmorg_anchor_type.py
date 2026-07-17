from odoo import fields, models


class PmorgAnchorType(models.Model):
    """Registry-ul închis al tipurilor de ancoră (ADR-002).

    Nucleul seedează tipurile generice; anchor pack-urile adaugă tipuri de
    domeniu prin propriile fișiere de date. Ce nu e aici nu există ca ancoră.
    """

    _name = "pmorg.anchor.type"
    _description = "Tip de ancoră PMORG"
    _order = "code"

    code = fields.Char(required=True)
    model_name = fields.Char(required=True)
    pack = fields.Char(required=True, help="Addon-ul care declară tipul.")
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint("UNIQUE (code)", "Codul există deja.")
    _model_unique = models.Constraint(
        "UNIQUE (model_name)", "Modelul are deja un tip de ancoră."
    )
