from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ZBSCron(models.Model):
    _inherit = "zbs.start"
    _name = "zbs.cronstart"
    _description = "trigger:cronjob"

    name = fields.Char(required=True)
    cronjob_ids = fields.One2many("ir.cron", "zbs_crontrigger_id", string="Cronjobs")
    pipeline_ids = fields.Many2many("zbs.pipeline", string="Pipelines")
    no_double_starts = fields.Boolean("Wait Finished", default=True)

    @api.model
    def _start(self):
        for rec in self:
            for pipe in rec.pipeline_ids:
                if rec.no_double_starts:
                    if pipe.cronjob_ids.filtered(
                        lambda x: x.state in ["pending", "running"]
                    ):
                        continue
                pipe.start(
                    {},
                    initiated_by="cronjob",
                    environment={
                        "cronstart": True,
                    },
                )

    def open_cronjobs(self):
        self.ensure_one()
        jobs = self.env["ir.cron"].search([("zbs_crontrigger_id", "=", self.id)])
        if not jobs:
            vals = jobs.with_context(
                active_model=self._name, active_id=self.id
            ).default_get([])
            vals["zbs_crontrigger_id"] = self.id
            jobs = jobs.create(vals)
        return {
            "name": self.name,
            "view_type": "form",
            "res_model": "ir.cron",
            "domain": [("zbs_crontrigger_id", "in", self.ids)],
            "views": [(False, "tree"), (False, "form")],
            "type": "ir.actions.act_window",
            "target": "current",
            "context": {
                "default_zbs_crontrigger_id": self.id,
                "default_active": True,
                "active_model": self._name,
                "active_id": self.id,
            },
        }

    @api.constrains("name")
    def _update_names_in_cronjobs(self):
        for rec in self:
            if rec.cronjob_ids:
                rec.cronjob_ids.sudo().write({"name": rec.name})
