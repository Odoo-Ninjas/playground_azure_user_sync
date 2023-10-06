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
from .test_pipe import ZBSPipelineCase


class TestTransformer(ZBSPipelineCase):

    def test_transformer(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "keep input filter"
        pipeline = form.save()

        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps([{"f1": "v1"}])},
        )

        code = (
            "data[0]"
        )

        worker, line = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_transformer_python"),
            {"code": code},
        )
        line.keep_input_filter = False
        instance = pipeline.start({})
        instance.heartbeat()
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(data._d, [{"f1": "v1"}])

    def test_last_execution_date(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "keep input filter"
        pipeline = form.save()

        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps({"f1": "v1"})},
        )

        code = "123"

        worker, line = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_transformer_python"),
            {"code": code, "propagate_code_result": True},
        )

        instance = pipeline.start({})
        instance.heartbeat()
        instance.heartbeat()
        d1 = fields.Datetime.from_string("1980-04-04 01:02:03")
        instance.date_start = d1

        instance = pipeline.start({})
        instance.heartbeat()
        instance.heartbeat()
        time.sleep(1)
        self.assertEqual(instance._get_env()._d, {'last_execution_date': d1})
