from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ZebrooSet(models.AbstractModel):
    _inherit = "zebrooset"

    @api.model
    def _prepare_dump(self, data):
        res = super()._prepare_dump(data)
        return res

    @api.model
    def _prepare_load(self, data):
        res = super()._prepare_load(data)
        return res
