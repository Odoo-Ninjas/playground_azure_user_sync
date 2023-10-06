from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class WizardNewEl(models.TransientModel):
    _name = "zbs.wiz.new.el"

    pipeline_id = fields.Many2one("zbs.pipeline", "Pipeline", required=True)
    model_id = fields.Many2one("ir.model", string="Type", required=True)
    filter_model_ids = fields.Many2many("ir.model")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)

        def collect():
            for model in self.env["zbs.tools"]._get_subclasses("zbs.worker"):
                obj = self.env[model]
                if isinstance(obj, models.Model):
                    yield model

        allowed_models = self.env["ir.model"].search([("model", "in", list(collect()))])
        assert self.env.context.get('active_model') == 'zbs.pipeline'
        res['pipeline_id'] = self.env.context.get('active_id')
        res["filter_model_ids"] = allowed_models.ids
        return res

    def ok(self):
        worker = self.env[self.model_id.model].create({
            'name': '-',
        })
        self.pipeline_id.line_ids.create({
            'worker_id': f"{worker._name},{worker.id}",
            'sequence': 999,
            'pipeline_id': self.pipeline_id.id,
        })
        return worker

