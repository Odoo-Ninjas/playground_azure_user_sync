from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class PipelineVersion(models.Model):
    _name = "zbs.pipeline.version"
    _order = "date desc"

    pipeline_id = fields.Many2one("zbs.pipeline", xport_ignore=True, ondelete="cascade", required=True)

    date = fields.Datetime("Date", default=lambda self: fields.Datetime.now())
    content = fields.Text("Content")

    def download(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/zync_download/{self.id}',
            'target': 'self',
        }