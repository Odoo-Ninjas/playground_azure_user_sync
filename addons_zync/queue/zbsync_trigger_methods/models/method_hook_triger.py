from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools.sql import table_exists
from odoo.tools.safe_eval import safe_eval


class TriggerMethodHook(models.Model):
    _inherit = "method_hook.trigger.mixin"
    _name = "zbs.trigger.methodhook"

    trigger_id = fields.Many2one("zbs.trigger", string="Trigger", ondelete="cascade")

    def _trigger(self, instances, args_packed, method):
        self.trigger_id._start_by_methodhook(instances, args_packed, method)
