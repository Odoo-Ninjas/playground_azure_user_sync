from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class BaseWizard(models.AbstractModel):
    _name = 'zbsync.base_wizard'

    name = fields.Char(default="Name the wizard")
    sample_file = fields.Binary("Sample File")

    def fill_pipeline(self):
        raise NotImplementedError("Create me")

    def button_ok(self):
        pipeline = self.env['zbs.pipeline'].create({
        })

        self.fill_pipeline(pipeline)

        return {
            'view_type': 'form',
            'res_model': pipeline._name,
            'res_id': pipeline.id,
            'views': [(False, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }


