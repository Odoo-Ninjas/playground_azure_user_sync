from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class PyFunc(models.Model):
    _name = "zbs.mapping.pyfunc"

    code = fields.Text("Code", help="objects: record")
    name = fields.Char("Name")
