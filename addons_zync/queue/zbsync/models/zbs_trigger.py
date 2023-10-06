from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ZBSTrigger(models.Model):
    _inherit = "zbs.worker"
    _name = "zbs.trigger"
    _description = "trigger:event"

    def process(self, instance, data):
        return instance.Result(data)