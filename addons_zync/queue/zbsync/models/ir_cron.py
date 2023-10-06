from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class IrCron(models.Model):
    _inherit = "ir.cron"
    zbs_crontrigger_id = fields.Many2one("zbs.cronstart", string="ZBS Cron Trigger")

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("active_model") == "zbs.pipeline":
            pipeline = self.env["zbs.pipeline"].browse(
                self.env.context.get("active_id")
            )
            for data in vals_list:
                data["name"] = pipeline.name
                data["model_id"] = self.env.ref("base.model_ir_cron").id

        res = super().create(vals_list)
        res._set_code()
        return res

    @api.constrains("zbs_contrigger_id")
    def _set_code(self):
        for rec in self:
            if rec.zbs_crontrigger_id:
                rec.code = (
                    f"model.browse("
                    f"{rec.zbs_crontrigger_id.id})._start(initiated_by='cronjob')"
                )
