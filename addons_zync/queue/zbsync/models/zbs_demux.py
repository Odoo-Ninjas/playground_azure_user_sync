from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class ZBSPipelineDemux(models.Model):
    _inherit = 'zbs.worker'
    _name = 'zbs.demuxer'
