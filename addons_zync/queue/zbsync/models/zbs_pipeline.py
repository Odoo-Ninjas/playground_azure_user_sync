from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from .zebrooset import ZebrooSet
import json

# TODO make buttons in forms


class ZBSPipeline(models.Model):
    _inherit = ["mail.thread", "zbs.xport.mixin"]
    _name = "zbs.pipeline"

    name = fields.Char("Name", required=True)
    line_ids = fields.One2many("zbs.pipeline.line", "pipeline_id", "Lines", copy=True)
    sequence_id = fields.Many2one(
        "ir.sequence",
        string="Sequence",
        default=lambda self: self.env.ref("zbsync.sequence_zbs_instance").id,
        xport_ignore=True,
    )
    tag_ids = fields.Many2many("zbs.pipeline.tag", string="Tags")
    cronjob_ids = fields.Many2many(
        "zbs.cronstart", string="Cronjobs", xport_ignore=True
    )
    queuejob_channel = fields.Char("Queuejob Channel", default="root")
    limit_parallel_runs = fields.Integer("Limit Parallel Runs", default=1)
    keep_instances_for_days = fields.Integer("Keep Instances For Days", default=20)
    version_ids = fields.One2many("zbs.pipeline.version", "pipeline_id", "Versions")
    logoutput = fields.Selection(
        [
            ("odoo_logs", "Odoo-Logs"),
            ("db", "Database"),
        ],
       default="odoo_logs",
       required=True,
    )

    def snapshot(self):
        for rec in self:
            rec.version_ids = [(0, 0, {"content": json.dumps(rec.dump(), indent=4)})]

    @api.constrains("limit_parallel_runs")
    def _check_limit_parallel_runs(self):
        for rec in self:
            if rec.limit_parallel_runs < 0:
                raise ValidationError(_("Limit Parallel Runs must be at least 0."))

    def run_test(self, return_instance=False):
        self.env["zbs.instance"].search(
            [("pipeline_id", "=", self.id), ("test_mode", "=", True)]
        ).unlink()
        res = self._make_instance(test_mode=True)
        return res

    def start_from_ui(self):
        return self._make_instance(test_mode=False)

    def _make_instance(self, test_mode=None):
        self.ensure_one()
        instance = self.start(data=None, test_mode=test_mode)
        self.env.cr.commit()
        instance._start()

        if test_mode:
            batches = instance.next_line_id.batch_ids.filtered(lambda x: x.state == 'failed')
            if batches:
                breakpoint()
        return {
            "view_type": "form",
            "res_model": instance._name,
            "res_id": instance.id,
            "views": [(False, "form")],
            "type": "ir.actions.act_window",
            "target": "current",
        }

    def show_lines(self):
        return {
            "name": _("Lines"),
            "view_type": "form",
            "res_model": "zbs.pipeline.line",
            "domain": [("pipeline_id", "=", self.id)],
            "context": {"default_pipeline_id": self.id},
            "views": [(False, "kanban")],
            "type": "ir.actions.act_window",
            "target": "current",
        }

    def show_instances(self):
        return {
            "name": _("Instances"),
            "view_type": "form",
            "res_model": "zbs.instance",
            "domain": [("pipeline_id", "=", self.id)],
            "views": [(False, "tree"), (False, "form")],
            "type": "ir.actions.act_window",
            "target": "current",
        }

    def start(self, data, initiated_by=None, environment=None, test_mode=False):
        self.ensure_one()
        assert initiated_by in ["cronjob", "manual", None]
        instance = self.env["zbs.instance"].sudo().create({"pipeline_id": self.id})
        if environment:
            instance.environment = self.env["zebrooset"].dumps(environment)
        if data:
            instance.initial_data = self.env["zebrooset"].dumps(data)
        instance.origin = initiated_by
        instance.test_mode = test_mode
        instance.next_line_id = instance.line_ids.sorted()[0]
        return instance

    def add_worker(self):
        return {
            "view_type": "form",
            "res_model": "zbs.wiz.new.el",
            "views": [(False, "form")],
            "context": {
                "default_pipeline_id": self.id,
            },
            "type": "ir.actions.act_window",
            "target": "new",
        }

    def copy(self, defaults=None):
        self = self.with_context(nostart_stop=True, zync_import=True)
        res = super(ZBSPipeline, self).copy(defaults)
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res._make_sure_startstop()
        return res

    def _make_sure_startstop(self):
        if self.env.context.get("nostart_stop"):
            return
        for rec in self:
            starters = rec.line_ids.filtered(lambda x: x.worker_id._name == "zbs.start")
            if not starters:
                start = self.env["zbs.start"].create({})
                rec.line_ids = [
                    [
                        0,
                        0,
                        {
                            "worker_id": f"{start._name},{start.id}",
                            "sequence": 999999,
                        },
                    ]
                ]
            stoppers = rec.line_ids.filtered(lambda x: x.worker_id._name == "zbs.stop")
            if not stoppers:
                stop = self.env["zbs.stop"].create({})
                rec.line_ids = [
                    [
                        0,
                        0,
                        {
                            "worker_id": f"{stop._name},{stop.id}",
                            "sequence": 999999,
                        },
                    ]
                ]

    def _resequence(self):
        for i, line in enumerate(self.line_ids.sorted()):
            if line.sequence != i:
                line.sequence = i

    def _add_worker(self, worker):
        self.line_ids = [
            [
                0,
                0,
                {
                    "worker_id": f"{worker._name},{worker.id}",
                    "sequence": 100,
                },
            ]
        ]

    @api.constrains("name")
    def _updated_name_update_crons(self):
        for rec in self:
            if rec.cronjob_ids:
                self.env["ir.cron"].sudo().with_context(active_test=False).search(
                    [("zbs_crontrigger_id", "in", rec.cronjob_ids.ids)]
                ).write({"name": rec.name})
