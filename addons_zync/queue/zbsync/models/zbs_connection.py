from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ZBSConnection(models.AbstractModel):
    _inherit = ["zbs.xport.mixin"]
    _name = "zbs.connection"

    name = fields.Char("Name", required=True)


class ZBSConnectionUsernamePassword(models.AbstractModel):
    _name = "zbs.connection.mixin.usernamepassword"

    username = fields.Char("Username", required=True)
    password = fields.Char("Password", required=True)


class ZBSConnectionUsernamePassword(models.AbstractModel):
    _name = "zbs.connection.mixin.url"

    url = fields.Char("URL", required=True)

class ZBSConnectionUsernamePassword(models.AbstractModel):
    _name = "zbs.connection.mixin.hostport"

    host = fields.Char("Host", required=True)
    port = fields.Integer("Port", required=True)
