from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class MixinDumperGrabber(models.Model):
    _name = "zbs.odoo.mixin.connection"
    model = fields.Char("Model", required=False)

    is_local_connection = fields.Boolean(related="connection_id.is_local_connection")
    connection_id = fields.Many2one(
        "zbs.connection.odoo", string="Connection", required=False
    )
