from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
class Tools(models.AbstractModel):
    _inherit = 'zbs.tools'

    @api.model
    def with_delay(self, instance, enabled, *args, **kwargs):
        if enabled:
            return instance.with_delay(*args, **kwargs)
        else:
            return instance