import psycopg2
import threading
import traceback
from datetime import timedelta
from odoo import _, api, fields, models, SUPERUSER_ID, registry
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import registry
from odoo.addons.queue_job.exception import RetryableJobError
from datetime import date, datetime, timedelta
from .zebrooset import ZebrooSet

try:
    from odoo.tools.safe_eval import wrap_module
except ImportError:
    from odoo.tools import wrap_module
import arrow
import logging

logger = logging.getLogger("zbs.zbs_instance")


class ZBSInstance(models.Model):
    _inherit = "mail.thread"
    _name = "zbs.instance"
    _order = "id desc"

    name = fields.Char("Name", required=True)
    initial_data = fields.Text("Initial Data")
    origin = fields.Char("Origin")
    tag_ids = fields.Many2many("zbs.pipeline.tag", related="pipeline_id.tag_ids")
    next_line_id = fields.Many2one("zbs.instance.line", string="Current Line")
    prev_line_id = fields.Many2one("zbs.instance.line", compute="_compute_prev_line")
    prev_line_override_id = fields.Many2one("zbs.instance.line")
    line_ids = fields.One2many("zbs.instance.line", "instance_id", string="Lines")
    pipeline_id = fields.Many2one(
        "zbs.pipeline",
        ondelete="cascade",
        required=True,
    )
    test_mode = fields.Boolean("Test-Mode", tracking=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("running", "Running"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        default="pending",
        required=True,
        tracking=True,
    )
    is_main = fields.Boolean(
        "Is Main Run",
        default=True,
        help="If batched and splitted away, the children have false here; used to distinguish parallel runs",
    )
    date_start = fields.Datetime("Date Started", tracking=True)
    date_stop = fields.Datetime("Date Stopped", tracking=True)
    last_error = fields.Text("Last Error", compute="_compute_last_error")
    environment = fields.Text(
        "Environment", help="Basically a python dict that contains environmental data."
    )
    last_heartbeat = fields.Datetime("Last Heartbeat", tracking=True)

    @api.depends(
        "next_line_id",
        "next_line_id.batch_ids",
        "next_line_id.batch_ids.err_desc",
    )
    def _compute_last_error(self):
        for rec in self:

            def failed(x):
                return x.state == "failed"

            current_batches = rec.mapped("next_line_id").filtered(failed)
            prev_batches = rec.mapped("prev_line_id").filtered(failed)
            batches = current_batches or prev_batches
            errors = []
            for batch in batches:
                if batch.err_desc:
                    errors.append(f"Batch {batch.name}:")
                    errors.append(batch.err_desc)
            rec.last_error = "\n".join(errors)

    @api.constrains("next_line_id")
    def _check_next_line(self):
        for rec in self:
            if not rec.next_line_id:
                raise ValidationError("Next Line is required")

    def replay(self):
        prev_line = self.prev_line_id
        if prev_line:
            prev_line.make_current()
        self.env.cr.commit()
        self.env.clear()
        self.with_context(self._get_ui_context()).heartbeat()

    @api.autovacuum
    def _gc_cleanup(self, *args, **kwargs):
        for pipeline in self.env["zbs.pipeline"].search([]):
            delta = timedelta(days=pipeline.keep_instances_for_days)
            crit = fields.Datetime.now() - delta
            self.search(
                [
                    ("pipeline_id", "=", pipeline.id),
                    ("state", "in", ["success", "failed"]),
                    ("date_stop", "<", crit),
                ]
            ).unlink()

    def _zbs_message_post(self, *args, **kwargs):
        self.message_post(*args, **kwargs)

    @api.depends("next_line_id")
    def _compute_prev_line(self):
        for rec in self:
            if rec.prev_line_override_id:
                rec.prev_line_id = rec.prev_line_override_id.id
                continue

            lines = list(rec.line_ids.sorted())
            if not rec.next_line_id:
                rec.prev_line_id = False
            index = lines.index(rec.next_line_id) - 1 if rec.next_line_id else -1
            if index < 0:
                rec.prev_line_id = lines[0]
            else:
                rec.prev_line_id = lines[index]

    def _eval_data(self):
        if not self.prev_line_id:
            data = self.line_ids.load_data(self.initial_data)
        else:
            data = self.prev_line_id._get_data()
        data = self._prepare_process_data(data)
        return data

    def Result(self, data, **kwargs):
        from .zbs_batch import ProcessResult

        return ProcessResult(data, **kwargs)

    def _filter_records(self, rec):
        if not self.next_line_id.range:
            return rec
        if isinstance(rec, models.Model):
            instances = rec.browse()
            for i, record in enumerate(rec, 1):
                if self.next_line_id.isinrange(i):
                    instances |= rec
            return instances

        rec2 = []
        for i, record in enumerate(rec, 1):
            if self.next_line_id.isinrange(i):
                rec2.append(record)
        return self.env["zebrooset"].rs(rec2)

    def _get_env(self):
        self.ensure_one()
        instance_env = self.env["zebrooset"].loads(self.environment or "{}")
        return instance_env

    def _set_env(self, env):
        self.ensure_one()
        if not env:
            env = self.env["zebrooset"].loads("{}")
        self.environment = env._dumps(env, env=self.env)

    def _get_default_objects(self, defaults):
        arrow2 = wrap_module(__import__("arrow"), ["get"])
        from pathlib import Path
        from . import SkipRecord

        logger = logging.getLogger("zync")

        d = defaults
        d["SkipRecord"] = SkipRecord
        d.setdefault("datetime", datetime)
        d.setdefault("date", date)
        d.setdefault("timedelta", timedelta)
        d.setdefault("arrow", arrow2)
        d.setdefault("Path", Path)
        d["env"] = self.env
        for k in ["instance_env"]:
            d[k] = self.env.context.get(k, d.get(k))
        if self.env.context.get("instance"):
            instance = self.env.context["instance"]
            logger = logging.getLogger(f"zync.{instance.pipeline_id.name}")
        d["logger"] = logger
        d["instance"] = instance
        d["instance_line"] = self.env.context.get("pipeline")
        d["last_execution_date"] = (d["instance_env"] or {}).get(
            "last_execution_date", None
        )

        def log(text, level="info"):
            pipeline = self.env.context.get("pipeline")
            if pipeline:
                pipeline.log(text, level)

        d["log"] = log
        return d

    def _check_running_count_and_prepare(self):
        self.state = "running"
        self.last_heartbeat = fields.Datetime.now()

        count_running = self.env["zbs.instance"].search_count(
            [
                ("pipeline_id", "=", self.pipeline_id.id),
                ("is_main", "=", True),
                ("test_mode", "=", False),
                ("state", "not in", ["success", "failed"]),
                ("id", "<", self.id),
            ]
        )
        if (
            count_running > self.pipeline_id.limit_parallel_runs
            and self.pipeline_id.limit_parallel_runs
        ):
            if not getattr(
                threading.current_thread(), "testing", None
            ) and not self.env.context.get("zbs_ignore_parallel_runs"):
                raise RetryableJobError(
                    "Too many parallel jobs",
                    seconds=10,
                    ignore_retry=True,
                )

    def _eval_condition(self, line, data):
        condition_code = line.original_line_id.condition
        condition = True
        if condition_code and condition_code != "True":
            condition = (
                self.env["zbs.tools"]
                .with_context(instance=self)
                .exec_get_result(condition_code, {"input": data, "data": data})
            )
        return condition

    def _make_batches(self, data, batchsize):
        self.ensure_one()

        data = self._filter_records(data)
        for batch in self._make_batches_technical(data, batchsize):
            dumped = self.line_ids.dump_data(batch["batch"])
            self.next_line_id.batch_ids = [
                [
                    0,
                    0,
                    {
                        "state": "todo",
                        "start": batch["start"],
                        "stop": batch["stop"],
                        "length": batch["length"],
                        "input_data": dumped,
                    },
                ]
            ]
        self.next_line_id.generated_batches = True

    def _make_batches_technical(self, rs, batchsize):
        def yieldbatch(index, batch):
            return {
                "start": index,
                "batch": batch,
                "stop": index + len(batch),
                "length": len(batch),
            }

        batch = []
        if not batchsize:
            yield {
                "start": 0,
                "length": len(rs),
                "batch": rs,
                "stop": len(rs),
            }
        else:
            did_any, started = False, 0
            for index, rec in enumerate(rs._iterate_records()):
                did_any = True
                if len(batch) < batchsize:
                    batch.append(rec)
                else:
                    yield yieldbatch(started, batch)
                    batch = [rec]
                    started = index
            if batch or not did_any:
                yield yieldbatch(started, batch)

    def _prepare_process_data(self, input):
        if isinstance(input, models.Model):
            return input
        if input is None:
            # execute at least once if None is providing, indicating are start
            # A [] means, nothing to run, because no input given
            input = [{}]
        if not isinstance(input, (dict, list)) and not isinstance(input, ZebrooSet):
            input = [input]
        if isinstance(input, list):
            input = self.env["zebrooset"].rs(input)
        return input

    def _heartbeat_exec_run(self, worker, prepared_data, context):
        try:
            with self.env["zbs.tools"].new_env() as env:
                # start worker sets start time for instance and changes instance
                worker = worker.with_env(env)
                self2 = self.with_env(env)
                context["zbs_logoutput"] = self2.pipeline_id.logoutput
                context["zbs_instance_devmode"] = self2.test_mode
                for k, v in context.items():
                    if isinstance(v, models.BaseModel):
                        context[k] = v.with_env(env)
                possible_process_result = worker.with_context(context).process(
                    self2, data=prepared_data
                )

                process_result = self._eval_bare_process_result(possible_process_result)
                if process_result and process_result.after_commit:
                    process_result.after_commit()
                return process_result

        except (
            psycopg2.errors.InFailedSqlTransaction,
            psycopg2.errors.SerializationFailure,
        ) as ex:
            self._raise_retry()

    def _raise_retry(self, ex):
        raise RetryableJobError(
            "Serialize Error - retrying",
            seconds=10,
            ignore_retry=True,
        ) from ex

    def _all_batches_done(self):
        self.ensure_one()
        return all(
            x.state in ["success", "failed"]
            for x in self.mapped("next_line_id.batch_ids")
        )

    def _goto_next_line(self):
        if self.test_mode or self.env.context.get("zbs_heartbeat_ui"):
            continue_immediately = False
        else:
            continue_immediately = self.next_line_id.continue_immediately

        # all batches must be done:
        if not self._all_batches_done():
            return False

        success = all(
            x.state == "success" for x in self.mapped("next_line_id.batch_ids")
        )
        if not success:
            self.state = "failed"
            return False

        next_line = self.next_line(self.next_line_id) or False
        if next_line:
            if next_line != self.next_line_id:
                self.next_line_id = next_line
        else:
            continue_immediately = False
        if next_line:
            next_line._reset_processed()
        return continue_immediately

    def _get_ui_context(self):
        return dict(
            ZBS_RAISE_ERROR=True,
            zbs_ignore_parallel_runs=True,
            zbs_heartbeat_ui=True,
        )

    def heartbeat_ui(self):
        self.next_line_id.make_current()
        self.env.cr.commit()
        self.env.clear()
        self = self.with_context(self._get_ui_context())
        self.heartbeat()

    def heartbeat(self, apply_continuation_group=False):
        """
        :apply_continuation_group: if set it is like a usual restart
            happened; in this case the instance continues at the restart group
            example:
            * you export data to another system which does not allow
        """
        for rec in self:
            do_continue = False
            with self.env["zbs.tools"].pglock(f"{rec._name}:{rec.id}"):
                with self.env["zbs.tools"].new_env() as env:
                    # avoid dirty reads, that block later; cannot destroy advisory lock
                    rec2 = rec.with_env(env)
                    if apply_continuation_group:
                        self._eval_continuation_group()
                    rec2._check_running_count_and_prepare()
                    debug_data = {
                        "pipeline_name": rec2.pipeline_id.name,
                        "zbs_line_name": rec2.name,
                        "instance_env": rec2._get_env(),
                        "zbs_batchsize": rec2.next_line_id.original_line_id.batchsize,
                        "zbs_test_mode": rec2.test_mode,
                    }
                    context = dict(self.env.context)
                    for k, v in debug_data.items():
                        context[k] = v
                    rec2.with_context(context)._ensure_batches()
                    batch_ids = (
                        rec2.mapped("next_line_id.batch_ids")
                        .filtered(lambda x: x.state == "todo")
                        .ids
                    )
                    del rec2

                for batch_id in batch_ids:
                    self.env["zbs.instance.line.batch"].with_context(context).heartbeat(
                        batch_id
                    )

                with self.env["zbs.tools"].new_env() as env:
                    rec2 = rec.with_env(env)
                    do_continue = rec2._goto_next_line()
                    del rec2

                if do_continue:
                    rec.heartbeat()

    def _ensure_batches(self):
        if not self.next_line_id.generated_batches:
            data = self._eval_data()
            condition = self._eval_condition(self.next_line_id, data)
            batchsize = None

            if condition:
                batchsize = self.env.context["zbs_batchsize"]
            self._make_batches(data, batchsize=batchsize)

    @api.model
    def create(self, vals):
        pipeline = self.env["zbs.pipeline"].browse(vals["pipeline_id"])
        data = vals.get("data", None)
        if data:
            raise ValidationError(
                "Please call _start method to start the instance with data."
            )
        vals["name"] = pipeline.sequence_id.next_by_id()
        res = super().create(vals)
        res._transfer_lines()
        start = res.line_ids.filtered(lambda x: x.worker_id._name == "zbs.start")
        if not start:
            raise ValidationError("Missing start element")

        return res

    def _transfer_lines(self):
        for line in self.pipeline_id.line_ids.filtered(lambda x: x.enabled):
            linevals = line._copy_for_instance(self)
            linevals["instance_id"] = self.id
            self.line_ids.create(linevals)

    @property
    def identity_key(self):
        self.ensure_one()
        return f"pipe#{self.pipeline_id.id}#instance#{self.id}"

    @api.model
    def cron_heartbeat(self):
        for rec in self.search(
            [("state", "in", ["pending", "running"]), ("test_mode", "=", False)],
            order="last_heartbeat desc",
        ):
            try:
                self.env["zbs.tools"].pg_advisory_lock(f"heartbeat_{rec.id}")
            except RetryableJobError:
                continue

            try:
                self.env["zbs.tools"].with_delay(
                    rec,
                    enabled=True,
                    identity_key=rec.identity_key,
                    channel=rec.pipeline_id.queuejob_channel,
                ).heartbeat(apply_continuation_group=True)
            except Exception as ex:
                logger.error(str(ex), exc_info=True)

    def next_line(self, current_line):
        lines = self.line_ids.sorted()
        index = list(lines.ids).index(current_line.id)
        if index + 1 >= len(lines):
            return None
        return lines[index + 1]

    def clear_messages(self):
        for rec in self:
            self.env["mail.message"].sudo().search(
                [("model", "=", self._name), ("res_id", "=", rec.id)]
            ).unlink()

    def retry(self):
        self.state = "running"

    def abort(self):
        self.state = "failed"
        self.message_post(body="User aborted")

    def _eval_continuation_group(self):
        if not self.next_line_id.original_line_id.group_continue_here:
            return
        line = self.next_line_id
        group = line.original_line_id.group_continue_here
        while line._get_prev_line().original_line_id.group_continue_here == group:
            line = line._get_prev_line()

        if line != self.next_line_id:
            line.make_current()

    def _start(self):
        if self.next_line_id and self.next_line_id.continue_immediately:
            self.heartbeat()

    def goto_end(self):
        stopline = self.line_ids.filtered(lambda x: x.worker_id._name == 'zbs.stop')
        self.prev_line_override_id = self.next_line_id
        self.next_line_id = stopline.id
