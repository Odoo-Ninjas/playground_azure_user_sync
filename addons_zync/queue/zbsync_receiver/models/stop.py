from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class Stop(models.Model):
    _inherit = "zbs.stop"

    return_data = fields.Boolean("Return Data")
    content_type = fields.Char("Content Type", default="application/json")

    def process(self, instance, data):
        res = super().process(instance, data)
        if not self.return_data:
            res = instance.Result(None)
        return res
