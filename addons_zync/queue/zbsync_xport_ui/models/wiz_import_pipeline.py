from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import base64
import json

class WizImportPipeline(models.Model):
    _name = 'zbs.import.pipeline'

    json_content = fields.Text("JSON")
    filecontent = fields.Binary("JSON Content")

    def ok(self):
        content = base64.b64decode(self.filecontent)
        content = json.loads(content)
        pipeline = self.env['zbs.pipeline'].load(content)
        return {
            'view_type': 'form',
            'res_model': pipeline._name,
            'res_id': pipeline.id,
            'views': [(False, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }