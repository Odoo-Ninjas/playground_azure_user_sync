from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from datetime import datetime


class ZBSStart(models.Model):
    _inherit = "zbs.worker"
    _name = "zbs.start"

    def is_start(self):
        return True

    def process(self, instance, data):
        from .zebrooset import ZebrooSet
        instance.date_start = fields.Datetime.now()

        data = instance.initial_data or None
        data = instance.line_ids.load_data(data)
        if isinstance(data, ZebrooSet):
            data._wraplist()

        # get last execution date
        domain = [
            ("pipeline_id", "=", instance.pipeline_id.id),
            ("origin", "=", instance.origin),
            ("id", "<", instance.id),
        ]
        prev_instance = instance.search(domain, limit=1, order="id desc")
        if prev_instance:
            last_execution_date = prev_instance.date_start
        else:
            last_execution_date = fields.Datetime.from_string("1980-04-04 00:00:00")
        instance_env = instance._get_env()
        instance_env["last_execution_date"] = last_execution_date
        instance._set_env(instance_env)
        return instance.Result(data)
