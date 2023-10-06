from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from .zebrooset import ZebrooSet
from odoo import registry
import logging

logger = logging.getLogger("zbs.pipeline")


class ZBSPipelineLine(models.Model):
    _inherit = ["zbs.xport.mixin"]
    _name = "zbs.pipeline.line"
    _order = "sequence"

    name = fields.Char(compute="_compute_name")
    batchsize = fields.Integer("Batch Size", default=0)
    group_continue_here = fields.Char("Continue Here Group")

    def _compute_name(self):
        for rec in self:
            if not rec.pipeline_id:
                rec.name = "-"
                continue
            rec.name = (
                f"{rec.pipeline_id.name}:"
                f"{rec.sequence}:{rec.worker_id._name}:{rec.worker_id.name}"
            )

    pipeline_id = fields.Many2one(
        "zbs.pipeline",
        "Pipeline",
        required=False,
        ondelete="cascade",
        xport_ignore=True,
    )
    sequence = fields.Integer("Sequence")
    loglevel = fields.Selection(
        [
            ("debug", "Debug"),
            ("info", "Info"),
            ("warning", "Warning"),
            ("error", "Error"),
            ("critical", "Critical"),
        ],
        "Log Level",
        default="info",
    )
    condition = fields.Text("Condition", default="True")
    logged = fields.Text("Log")
    own_queuejob = fields.Boolean("Job", default=False)
    worker_id = fields.Reference(
        selection="_get_worker_selection", string="Worker", required=True
    )
    ttype_name = fields.Char("Type", compute="_compute_typename")
    enabled = fields.Boolean("Enabled", default=True)
    continue_immediately = fields.Boolean("Continue immediatley", default=False)

    can_open_worker_detail = fields.Boolean(
        compute="_compute_can_open_worker_detai", store=False
    )

    keep_input_filter = fields.Char(
        "Keep Input Filter",
        help=(
            "* to keep source record; record.a.b.c to select specific data; "
            "can be semicolon separated; input.a.b.c; "
            "{'f1': input.f1}"
        ),
    )
    range = fields.Char("Range", help="like 1,2,3 or 1-3,8-5")
    path_content = fields.Char("Path Content", help="Where to start iterating data from e.g. data[5].field1.records")

    @api.depends("worker_id")
    def _compute_typename(self):
        for rec in self:
            rec.ttype_name = rec.worker_id._name

    def _get_worker_selection(self):
        return self.env["zbs.worker"].zbs_sub_classes_for_selection()

    def process(self, input):
        return self.worker_id.process(self, input)

    @api.model
    def load_data(self, data):
        data = data or ""
        if not data:
            return None
        if data.startswith("ODOO:"):
            _, model, ids = data.split(":")
            ids = ids and map(int, ids.split(",")) or []
            return self.env[model].browse(ids)

        elif data.startswith("ZebrooSet:"):
            return ZebrooSet._loads(data.split("ZebrooSet:", 1)[1], env=self.env)
        elif isinstance(data, (list, dict)):
            return ZebrooSet(data)
        elif isinstance(data, str):
            return ZebrooSet._loads(data, env=self.env)
        else:
            raise NotImplementedError(data)

    @api.model
    def dump_data(self, data):
        if not isinstance(data, (models.Model, list, dict,ZebrooSet)):
            data = [data]

        if isinstance(data, models.Model):
            return f"ODOO:{data._name}:{','.join(map(str, data.ids))}"
        elif isinstance(data, (list, dict, ZebrooSet)):
            if isinstance(data, ZebrooSet):
                data = data._d
            return "ZebrooSet:" + ZebrooSet._dumps(data, self.env)
        else:
            raise NotImplementedError(data)

    def open_worker(self):
        obj = self.env[self.worker_id._name].browse(self.worker_id.id)
        return obj.open()

    def open_worker_detail(self):
        obj = self.env[self.worker_id._name].browse(self.worker_id.id)
        return obj.open()

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if not self.env.context.get("zync_import"):
            # make sure there is start and end
            res.pipeline_id._make_sure_startstop()

            stoppers = res.pipeline_id.line_ids.filtered(
                lambda x: x.worker_id._name == "zbs.stop"
            )
            if stoppers[-1].sequence <= res.sequence:
                res.sequence, stoppers[-1].sequence = (
                    stoppers[-1].sequence,
                    res.sequence,
                )

            res.pipeline_id._resequence()

        return res

    def _copy_for_instance(self, instance):
        res = {
            "pipeline_id": self.pipeline_id.id,
            "sequence": self.sequence,
            "loglevel": self.loglevel,
            "own_queuejob": self.own_queuejob,
            "worker_id": f"{self.worker_id._name},{self.worker_id.id}",
            "enabled": self.enabled,
            "instance_id": instance.id,
            "original_line_id": self.id,
        }
        return res

    def open_line(self, css_class=""):
        return {
            "name": self.worker_id.name,
            "type": "ir.actions.act_window",
            "view_type": "form",
            "res_model": self._name,
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }

    def ok(self):
        return {"type": "ir.actions.act_window_close"}

    def isinrange(self, index):
        range = self.range
        if not range:
            return True
        for section in range.strip().split(","):
            section = section.strip().replace(" ", "")
            if "-" in section:
                start, end = section.split("-")
                if index >= int(start) and index <= int(end):
                    return True
            else:
                if index == int(section):
                    return True

    def _compute_can_open_worker_detai(self):
        for rec in self:
            rec.can_open_worker_detail = rec.worker_id.can_open_worker_detail

    @api.constrains("worker_id")
    def _continue_immediate_for_start(self):
        for rec in self:
            if rec.worker_id._name == "zbs.start":
                if not rec.continue_immediately:
                    rec.continue_immediately = True
