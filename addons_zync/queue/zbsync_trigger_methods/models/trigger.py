from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class Trigger(models.Model):
    _inherit = "zbs.trigger"

    method_trigger_ids = fields.One2many("zbs.trigger.methodhook", "trigger_id")

    def _start_by_methodhook(self, records, args, method):
        for pipeline in self._get_pipeline_lines().pipeline_id:
            for record in records:
                environment = self._prepare_environment(record, args, method)
                record = self.env["zebrooset"].dumps(records)
                pipeline.start(
                    record,
                    initiated_by="method_trigger",
                    environment=environment,
                )
            self = self.sudo()

    def _prepare_environment(self, record, args, method):
        environment = {
            "args": args["args"],
            "kwargs": args["kwargs"],
            "method": method,
        }
        if method == "write":
            environment["fields"] = sorted(args["args"][1].keys())
        return environment
