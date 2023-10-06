from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import logging

logger = logging.getLogger("zbsync.webworker")


class WebWorker(models.Model):
    _inherit = ["zbs.grabber"]

    _name = "zbs.web.worker"
    _description = "web.request (JSON, GET/POST/PUT)"

    endpoint_id = fields.Many2one("zbs.web.endpoint", "Endpoint")

    path = fields.Text(related="endpoint_id.path", inverse="_set_endpoint_values")
    method = fields.Selection(
        related="endpoint_id.method", inverse="_set_endpoint_values"
    )

    def _set_endpoint_values(self):
        for rec in self:
            rec.endpoint_id.method = rec.method
            rec.endpoint_id.path = rec.path

    def process_record(self, instance, index, record, data):
        result_record = self.endpoint_id.process(index, record, data)
        return result_record
