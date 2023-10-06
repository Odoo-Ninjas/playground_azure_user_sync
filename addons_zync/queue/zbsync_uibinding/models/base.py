from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
class Base(models.AbstractModel):
    _inherit = 'base'

    def start_action_zbsync_from_button(self):
        active_id = self.env.context['active_id']
        model = self.env.context['active_model']
        instance=self.env[model].browse(active_id)
        pipeline = self.env['zbs.pipeline'].browse(self.env.context['pipeline_id'])
        pipeline.start(instance)
        return True
