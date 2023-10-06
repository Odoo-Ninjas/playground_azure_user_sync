from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class ZBSDumperTestStructLine(models.Model):
    _name = "zbs.test.order.line"
    order_id = fields.Many2one("zbs.test.order")
    name = fields.Char()
    price = fields.Float()
    anyfield = fields.Char()
