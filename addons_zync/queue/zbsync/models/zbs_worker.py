from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from .zebrooset import ZebrooSet
from contextlib import contextmanager
from odoo.addons.zbsync.models.zebrooset import ZebrooSet, _WrappedList

"""
Call on iteration or where applicable:

keep_input = self._extract_input_information(record)
# merge it into the result

"""


# this is embedded in a pipeline element
class ZBSWorker(models.AbstractModel):
    _inherit = ["zbs.xport.mixin", "mail.thread"]
    _name = "zbs.worker"

    name = fields.Char("Name")
    can_open_worker_detail = fields.Boolean(compute="_compute_can_open_worker_detail")
    can_show_replay = fields.Boolean(compute="_compute_can_show_replay")
    comment = fields.Text("Comment")

    def _compute_can_show_replay(self):
        for rec in self:
            rec.can_show_replay = False

    def replay(self):
        raise NotImplementedError()

    def is_start(self):
        return False

    def is_end(self):
        return False

    def _get_pipelines(self):
        self.ensure_one()
        lines = self.env["zbs.pipeline.line"].search(
            [("worker_id", "=", f"{self._name},{self.id}")]
        )
        return lines

    def _iterate_data(self, data):
        if isinstance(data, (models.Model, ZebrooSet, list, dict)):
            if isinstance(data, (list, dict)):
                data = self.env["zebrooset"].rs(data)
            if isinstance(data, ZebrooSet) and isinstance(data._d, dict):
                data._d = [data._d]

            pipeline = self.env.context["pipeline"]
            if pipeline.path_content:
                data = self.env["zbs.tools"].exec_get_result(
                    pipeline.path_content, {"data": data}
                )

            if isinstance(data, (models.Model, ZebrooSet, list, _WrappedList)):
                for index, record in enumerate(data):
                    yield index, record
            else:
                yield 0, data
        else:
            yield 0, data

    def process(self, instance, data):
        from . import SkipRecord
        result = []
        for index, record in self._iterate_data(data):
            try:
                current = self.process_record(instance, index, record, data)
            except SkipRecord:
                continue
            self._apply_keep_input(index, record, data, current)
            result.append(current)
        return instance.Result(result)

    def process_record(self, instance, index, record, data):
        raise NotImplementedError("Please implement process record")

    def open_action(self):
        self.ensure_one()
        return {
            "view_type": "form",
            "res_model": self._name,
            "res_id": self.id,
            "views": [(False, "form")],
            "type": "ir.actions.act_window",
            "target": "current",
        }

    def _apply_keep_input(self, index, record, input_data, result_records):
        kept = self._keep_input(index, record, input_data)
        if isinstance(result_records, (dict, list)):
            result_records = self.env["zebrooset"].rs(result_records)
        if not kept:
            return
        for rec in result_records._iterate_records():
            self._apply_keep_input_merge_record(rec, kept)

    def _apply_keep_input_merge_record(self, rec, kept):
        rec._merge(kept)

    def _keep_input(self, index, record, input_data):
        input_data = (
            self.env["zebrooset"].rs(input_data)
            if isinstance(input_data, (dict, list))
            else input_data
        )
        batch = self.env.context['zbs_batch']
        line = self.env.context["pipeline"]
        keep_input_filter = self.env.context.get("keep_input_filter")
        assert line._name == "zbs.instance.line"
        batch._inc_processed()
        if not keep_input_filter:
            return {}
        if keep_input_filter == "*":
            return input_data
        if keep_input_filter == "record":
            return record
        if not keep_input_filter:
            return {}
        keep_filter = keep_input_filter.replace(";", ",")
        data = input_data
        if isinstance(data, (list, dict)):
            data = ZebrooSet(data)

        if "," in keep_filter:
            parts = list(map(lambda x: x.strip(), keep_filter.split(",")))
        else:
            parts = [keep_filter]
        result = self._keep_input_eval(parts, record, input_data, index)
        return result

    def _keep_input_eval(self, filters, record, input_data, index):
        result = {}
        for part in filters:
            partresult = self.env["zbs.tools"].exec_get_result(
                part,
                {
                    "record": record,
                    "data": input_data,
                    "input": input_data,
                    "index": index,
                },
            )
            if not isinstance(partresult, dict):
                name = part.split(".")[-1]
                partresult = {name: partresult}
            result = self.env["zebrooset"].rs(result)
            result._merge(partresult)
            result = result._d
        return result

    def _compute_can_open_worker_detail(self):
        for rec in self:
            rec.can_open_worker_detail = False

    def open(self):
        # fallback action
        self.ensure_one()
        return {
            "name": self.name,
            "view_type": "form",
            "res_id": self.id,
            "res_model": self._name,
            "views": [(False, "form")],
            "type": "ir.actions.act_window",
            "target": "current",
        }