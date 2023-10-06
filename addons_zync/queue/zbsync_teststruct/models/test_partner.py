from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ZBSDumperTestPartner(models.Model):
    _name = "zbs.test.partner"

    parent_partner_id = fields.Many2one("zbs.test.partner")
    line_ids = fields.One2many("zbs.test.order.line", "order_id")
    name = fields.Char()
    anyfield = fields.Char()
