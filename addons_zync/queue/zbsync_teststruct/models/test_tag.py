from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class ZBSDumperTestTag(models.Model):
    _name = "zbs.test.tag"

    name = fields.Char()
    anyfield = fields.Char()