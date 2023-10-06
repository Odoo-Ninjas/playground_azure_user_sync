from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ZBSGrabber(models.AbstractModel):
    _inherit = "zbs.worker"
    _name = "zbs.grabber"
