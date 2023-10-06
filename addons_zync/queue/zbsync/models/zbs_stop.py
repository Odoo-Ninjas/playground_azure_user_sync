from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ZBSStop(models.Model):
    _inherit = "zbs.worker"
    _name = "zbs.stop"

    def is_end(self):
        return False

    def process(self, instance, data):
        instance.state = 'success'
        instance.date_stop = fields.Datetime.now()
        return instance.Result(data)