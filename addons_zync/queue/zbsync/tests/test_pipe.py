import json
import os
from odoo import models
import pprint
import logging
import time
import uuid
from datetime import datetime, timedelta
from unittest import skipIf
from odoo import api
from odoo import fields
from odoo.tests.common import TransactionCase, Form
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, RedirectWarning, ValidationError, AccessError
from odoo.tests.common import Form
import arrow
from odoo.tools.safe_eval import safe_eval
try:
    from odoo.tools.safe_eval import wrap_module
except:
    from odoo.tools import wrap_module


class ZBSPipelineCase(TransactionCase):
    def make_simple_pipe(self, worker_class_name, worker_data):
        pipe = self.env["zbs.pipeline"].create(
            {
                "name": type(self).__name__,
            }
        )
        worker = self.env[worker_class_name].create(worker_data)
        line = self.env["zbs.pipeline.line"].create(
            {
                "pipeline_id": pipe.id,
                "sequence": 10,
                "worker_id": f"{worker._name},{worker.id}",
            }
        )
        debugger = self.env["zbs.debugger"].create(
            {
                "name": "debugger1",
            }
        )
        self.env["zbs.pipeline.line"].create(
            {
                "pipeline_id": pipe.id,
                "sequence": 10,
                "worker_id": f"{debugger._name},{debugger.id}",
            }
        )
        return pipe.with_context(ZBS_RAISE_ERROR=True), line

    def add_line(self, pipeline, worker_model, vals=None):
        assert isinstance(worker_model, models.AbstractModel)
        wiz_add = Form(
            self.env["zbs.wiz.new.el"].with_context(
                active_model=pipeline._name, active_id=pipeline.id
            )
        )
        wiz_add.model_id = worker_model
        lines = self.env["zbs.pipeline.line"].search([])
        wiz_add = wiz_add.save()
        worker = wiz_add.ok()
        if vals:
            worker.write(vals)
        lines = lines.search([]) - lines
        return worker, lines

    def test_make_pipe(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Hansi"
        pipeline = form.save()

        self.assertEqual(len(pipeline.line_ids), 2)

    def test_keep_input_filter(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "keep input filter"
        pipeline = form.save()

        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps({"f1": "v1"})},
        )

        worker, line = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps({"f2": "v2"})},
        )
        line.keep_input_filter = "{'f1': input.f1}"
        instance = pipeline.start({})
        instance.heartbeat()
        test = instance._eval_data()
        self.assertTrue(test)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(data._d, {"f1": "v1", "f2": "v2"})

    def test_keep_input_filter_at_records(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "keep input filter at records"
        pipeline = form.save()

        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps([{"f1": "v1"}, {"f1": "v2"}])},
        )

        worker, line = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps([{"f2": "v1"}, {"f2": "v2"}])},
        )
        line.keep_input_filter = "{'f1': input[index].f1}"
        instance = pipeline.start({})
        instance.heartbeat()
        test = instance._eval_data()
        self.assertTrue(test)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(data._d, [{"f1": "v1", "f2": "v1"}, {"f1": "v2", "f2": "v2"}])

    def test_domain_eval_arrow_lib(self):
        arrow2 = wrap_module(__import__('arrow'), ['get'])
        safe_eval("arrow.get()", {'arrow': arrow2})

    def test_if_condition_not(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "keep input filter at records"
        pipeline = form.save()

        worker_const1, line_const1 = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps([{"f": "v1"}])},
        )

        worker_const2, line_const2 = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps([{"f": "v2"}])},
        )
        line_const2.condition = "input.f != 'v1'"

        instance = pipeline.start({})
        for i in range(3):
            instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(data._d, [{"f": "v1"}])

    def test_if_condition(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "keep input filter at records"
        pipeline = form.save()

        worker_const1, line_const1 = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps([{"f": "v1"}])},
        )

        worker_const2, line_const2 = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps([{"f": "v2"}])},
        )
        line_const2.condition = "input.f == 'v1'"

        instance = pipeline.start({})
        for i in range(3):
            instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(data._d, [{"f": "v2"}])

    def test_batches(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "keep input filter at records"
        pipeline = form.save()

        worker_const1, line_const1 = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps([{"f": "v1"}, {"f": "v2"}])},
        )

        instance = pipeline.start({})
        while instance.state == "running":
            instance.heartbeat()

        data = instance._eval_data()
        self.assertEqual(data._d, [{"f": "v2"}])
