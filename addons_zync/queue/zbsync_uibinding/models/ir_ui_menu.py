from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class Menu(models.Model):
    _inherit = "ir.ui.menu"

    pipeline_id = fields.Many2one("zbs.pipeline", string="Pipeline")
