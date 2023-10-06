from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import base64


class WizFileUpload(models.Model):
    _name = "zbs.wiz.fileupload"

    filecontent = fields.Binary("Filecontent")
    filename = fields.Char("Filename")
    pipeline_id = fields.Many2one("zbs.pipeline", string="Pipeline")

    def ok(self):
        if not self.filecontent:
            raise UserError("Please upload a file!")
        content = base64.b64decode(self.filecontent)
        instance = self.pipeline_id.start(
            {
                "filename": self.filename,
                "filecontent": content,
            }
        )
        return {
            "view_type": "form",
            "res_model": instance._name,
            "res_id": instance.id,
            "views": [(False, "form")],
            "type": "ir.actions.act_window",
            "target": "current",
        }
