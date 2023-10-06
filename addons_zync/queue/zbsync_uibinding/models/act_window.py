from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ActWindow(models.Model):
    _inherit = "ir.actions.act_window"

    pipeline_id = fields.Many2one("zbs.pipeline", string="Pipeline")
