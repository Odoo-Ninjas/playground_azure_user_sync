from odoo import _, api, fields, models, SUPERUSER_ID, registry
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import logging

logger = logging.getLogger("ZBSLog")


class InstanceLine(models.Model):
    _inherit = "zbs.pipeline.line"
    _name = "zbs.instance.line"

    batches = fields.Text(compute="_compute_batches")
    batch_ids = fields.One2many("zbs.instance.line.batch", "line_id", string="Batches")

    is_current = fields.Boolean(string="Is Current", compute="_compute_is_current")
    original_line_id = fields.Many2one("zbs.pipeline.line")
    instance_id = fields.Many2one("zbs.instance")
    keep_input_filter = fields.Char(
        related="original_line_id.keep_input_filter", readonly=False
    )
    continue_immediately = fields.Boolean(
        related="original_line_id.continue_immediately"
    )
    processed_records = fields.Integer("Processed Records", compute="_compute_counter")
    name = fields.Char(related="original_line_id.name")
    path_content = fields.Char(related="original_line_id.path_content")
    generated_batches = fields.Boolean("Generated Batches")
    has_failed = fields.Boolean(compute="_compute_batches")
    only_success = fields.Boolean(compute="_compute_batches")

    def _compute_counter(self):
        count = {}
        with self.env["zbs.tools"].new_env() as env:
            for rec in self:
                env.cr.execute(
                    "select id from zbs_instance_line_batch where line_id = %s",
                    (rec.id,),
                )
                batch_ids = [x[0] for x in env.cr.fetchall()]
                env.cr.execute(
                    "select sum(amount) from zbs_batch_counter where batch_id in %s",
                    (tuple(batch_ids + [0]),),
                )
                count[rec.id] = env.cr.fetchone()[0]
        for rec in self:
            rec.processed_records = count[rec.id]

    def _reset_processed(self):
        for rec in self:
            self.env.cr.execute(
                "DELETE FROM zbs_instance_line_batch WHERE line_id = %s", (rec.id,)
            )
            self.invalidate_cache()
            rec.generated_batches = False

    @api.depends("instance_id.next_line_id")
    def _compute_is_current(self):
        for rec in self:
            rec.is_current = rec.instance_id.next_line_id == rec

    def make_current(self):
        self.ensure_one()
        self.instance_id.next_line_id = self
        if self.instance_id.next_line_id.worker_id.is_start():
            self.instance_id.next_line_id = self.instance_id.next_line(
                self.instance_id.next_line_id
            )
        self._reset_processed()
        self.instance_id.prev_line_override_id = False
        self.instance_id.state = "running"
        return True

    def open_logs(self):
        self.ensure_one()
        logs = self.mapped("batch_ids.log_ids")
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

    def open_batches(self):
        self.ensure_one()
        if len(self.batch_ids) == 1:
            return {
                "view_type": "form",
                "res_model": self.batch_ids._name,
                "res_id": self.batch_ids.id,
                "views": [(False, "form")],
                "type": "ir.actions.act_window",
                "target": "new",
            }
        return {
            "type": "ir.actions.act_window",
            "name": "Batches",
            "res_model": self.batch_ids._name,
            "domain": [("line_id", "=", self.id)],
            "views": [(False, "list"), (False, "form")],
            "target": "current",
        }

    def open_logs_list(self):
        self.ensure_one()
        logs = self.mapped("batch_ids.log_ids")
        if not logs:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": "Logs",
            "res_model": logs._name,
            "domain": [("line_id", "=", self.id)],
            "views": [(False, "list"), (False, "form")],
            "target": "current",
        }

    def log(self, message, level=None):
        logoutput = self.env.context.get("zbs_logoutput", None)

        if not logoutput:
            return

        if logoutput == "odoo_logs":
            self._log_odoologs(message, level)
        elif logoutput == "database":
            self._log_database(message, level)
        else:
            raise NotImplementedError(logoutput)

    def _log_odoologs(self, message, level):
        level_as_int = getattr(logging, level.upper())
        logger.log(level_as_int, message)

    def _log_database(self, message, level):
        Tools = self.env["zbs.tools"]
        level = level or "info"
        levels = list(map(lambda x: x[0], self._fields["loglevel"].selection))
        index = levels.index(level)
        index_crit = levels.index(self.loglevel)
        instance = self.instance_id
        logger.info(message)
        if index < index_crit and not instance.test_mode:
            return

        with self.env["zbs.tools"].new_env() as env:
            self.with_env(env)._append_log_text(message)

            if self.env.context.get("zbs_instance_devmode") or level == "error":
                instance.with_env(env).sudo().message_post(
                    body=str(message)[:1024],
                )

    def _append_log_text(self, message):
        self.logged = (self.logged or "") + (message or "") + "\n"

    def open_line(self, css_class=""):
        line = self.original_line_id
        if "open_batches" in css_class:
            return self.open_batches()
        return {
            "name": line.worker_id.name,
            "type": "ir.actions.act_window",
            "view_type": "form",
            "res_model": line._name,
            "res_id": line.worker_id.id,
            "views": [(False, "form")],
            "target": "new",
        }

    @api.depends("batch_ids", "batch_ids.state")
    def _compute_batches(self):
        for rec in self:
            states = {}
            for batch in rec.batch_ids:
                states.setdefault(batch.state, 0)
                states[batch.state] += 1
            text = []
            for state in ["todo", "failed", "success"]:
                text.append(f"{state}: {states.get(state, 0)}")
            rec.batches = " ".join(text)

            rec.has_failed = states.get("failed", 0) > 0
            rec.only_success = not states.get("todo") and not states.get("failed")

    def _get_data(self):
        self.ensure_one()
        data = []
        for batch in self.batch_ids:
            data += batch._get_data()
        return data

    def _get_prev_line(self):
        self.ensure_one()
        line_ids = self.instance_id.line_ids.sorted().ids
        idx = line_ids.index(self.id)
        if not idx:
            return self.env[self._name]
        return self.browse(line_ids[idx - 1])
