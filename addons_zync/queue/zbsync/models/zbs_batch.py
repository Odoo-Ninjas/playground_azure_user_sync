import psycopg2
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from .zebrooset import ZebrooSet
import traceback
import logging
from odoo.addons.queue_job.exception import RetryableJobError

logger = logging.getLogger("zbs.batch")


class BatchFailed(Exception):
    pass


class CounterTable(models.Model):
    _name = "zbs.batch.counter"

    batch_id = fields.Many2one(
        "zbs.instance.line.batch", ondelete="cascade", required=True, index=True
    )
    amount = fields.Integer("Count", default=0)


class ProcessResult(object):
    def __init__(self, data, after_commit=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data
        self.after_commit = after_commit


class Batch(models.Model):
    _name = "zbs.instance.line.batch"
    _order = "id"

    name = fields.Char(string="Name", _compute="compute_name")
    start = fields.Integer("Start")
    stop = fields.Integer("Stop")
    length = fields.Integer("Length")
    line_id = fields.Many2one("zbs.instance.line", string="Line")
    state = fields.Selection(
        [("todo", "Todo"), ("success", "Success"), ("failed", "Failed")],
        string="State",
        default="todo",
        required=True,
    )
    err_desc = fields.Text("Error")

    input_data = fields.Text("Input Data")
    output_data = fields.Text("Output Data")
    processed_records = fields.Integer("Processed Records", compute="_compute_counter")
    log_ids = fields.One2many("zbs.instance.logs", "batch_id", string="Logs")

    def _compute_name(self):
        for rec in self:
            parent_name = rec.line_id.name
            rec.name = parent_name + " - " + self.uistring

    @property
    def uistring(self):
        return f"{self.start} - {self.stop}: {self.state}"

    def _get_data(self):
        data = self.output_data or []
        data = self.env["zbs.instance.line"].load_data(data)
        return data

    # def _compute_input_data(self):
    #     for rec in self:
    #         data = (
    #             rec.line_id.prev_line_id and rec.line_id.prev_line_id._get_data() or []
    #         )

    #         if isinstance(data, ZebrooSet):
    #             data = list(data._iterate_records(start=rec.start, stop=rec.stop))
    #         elif isinstance(data, list):
    #             data = data[rec.start or None : rec.stop or None]
    #             data = ZebrooSet(data)
    #         else:
    #             data = ZebrooSet([])

    #         rec.input_data = self.env["zebrooset"].dumps(data)

    def _inc_processed(self, qty=1):
        with self.env["zbs.tools"].new_env() as env:
            for rec in self:
                self.env.cr.execute(
                    "INSERT INTO zbs_batch_counter"
                    "(batch_id, amount) "
                    "VALUES(%s, %s)",
                    (rec.id, qty),
                )

    def _compute_counter(self):
        with self.env["zbs.tools"].new_env() as env:
            env.cr.execute(
                "select sum(amount), batch_id "
                "from zbs_batch_counter "
                "where batch_id in %s "
                "group by batch_id ",
                (tuple(self.ids),),
            )
            counts = env.cr.fetchall()

        for rec in self:
            db = [x for x in counts if x[1] == rec.id]
            if not db:
                count = 0
            else:
                count = db[0][0] or 0
            rec.processed_records = count

    def open_logs(self):
        self.ensure_one()
        logs = self.log_ids
        if not logs:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": "Logs",
            "res_model": logs._name,
            "res_id": logs[0].id,
            "views": [(False, "form")],
            "target": "new",
            "flags": {
                "form": {
                    "action_buttons": False,
                    "initial_mode": "view",
                }
            },
        }

    def _log_process_result(self, started, process_result):
        if not process_result:
            return
        output_data = self.env["zbs.instance.line"].dump_data(process_result.data)
        self.log_ids.create(
            {
                "date_start": started,
                "date_stop": fields.Datetime.now(),
                "batch_id": self.id,
                "output_data": output_data,
            }
        )
        self.output_data = output_data
        self.line_id.log(str(process_result.data), "debug")

    @api.model
    def heartbeat(self, batch_id):
        local_data = {"result": None}

        def on_after_commit():
            result = local_data["result"]
            if result and result.after_commit:
                result.after_commit()

        with self.env["zbs.tools"].new_env(on_after_commit=on_after_commit) as env:
            try:
                context = self.env.context
                self = env[self._name].browse(batch_id).with_context(context)
                data = self.env["zbs.instance.line"].load_data(self.input_data)
                try:
                    local_data["result"] = self._exec_run(data)
                    self.state = "success"
                except BatchFailed:
                    self.state = "failed"
            except (
                psycopg2.errors.InFailedSqlTransaction,
                psycopg2.errors.SerializationFailure,
            ) as ex:
                raise RetryableJobError(
                    "Serialize Error - retrying", ignore_retry=True, seconds=10
                )

    def _exec_run(self, data):
        started = fields.Datetime.now()

        context = dict(
            pipeline=self.line_id,
            instance=self.line_id.instance_id,
            zbs_batch=self,
            instance_env=self.env.context["instance_env"],
            keep_input_filter=self.line_id.keep_input_filter,
        )
        try:
            result = self.line_id.worker_id.with_context(context).process(
                self.line_id.instance_id, data
            )
        except (
            psycopg2.errors.InFailedSqlTransaction,
            psycopg2.errors.SerializationFailure,
        ):
            raise
        except Exception as ex:
            if self.env.context.get("zbs_test_mode"):
                raise
            self._handle_exception(ex, started)
            raise BatchFailed()
            return False
        result = self._eval_bare_process_result(result)
        self._log_process_result(started, result)
        return result

    def _eval_bare_process_result(self, res):
        if res and not isinstance(res, ProcessResult):
            raise Exception(f"Expected type process result for {res}")
        process_result = res
        return process_result

    def _handle_exception(self, ex, started):
        pipeline_name = self.env.context["pipeline_name"]
        zbs_line_name = self.env.context["zbs_line_name"]
        logger.warn(
            f"{pipeline_name}-{zbs_line_name}",
            exc_info=True,
        )
        try:
            self.env.cr.rollback()
            self.env.clear()
        except psycopg2.errors.InterfaceError:
            logger.warn("Process seems to forcibly killed - no rollback required")
        try:
            with self.env["zbs.tools"].new_env() as env:
                self = self.with_env(env)
                self.state = "failed"
                last_exc = traceback.format_exc() + "\n" + str(ex)
                self.log_ids.create(
                    {
                        "batch_id": self.id,
                        "date_start": started,
                        "date_stop": fields.Datetime.now(),
                        "last_exception": last_exc.replace("\\n", "\n"),
                    }
                )
                self.err_desc = last_exc
                self.line_id.instance_id.message_post(body=last_exc)
        except Exception as ex:
            logger.warn(str(ex), exc_info=True)
