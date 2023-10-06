import odoo
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
from odoo.addons.zbsync.tests.test_pipe import ZBSPipelineCase
from ..controllers.receiver import Receiver
from .. import URL


class TestReceiver(ZBSPipelineCase, odoo.tests.HttpCase):
    def test_receiver(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "keep input filter"
        pipeline = form.save()

        worker, line = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps([{"f1": "v1"}])},
        )
        line.continue_immediately = True

        code = "data[0]"

        worker, line = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_transformer_python"),
            {"code": code},
        )
        line.continue_immediately = True
        line.keep_input_filter = False
        identifier = pipeline.line_ids[0].worker_id.identifier

        response = self.url_open(
            url=URL + "testing/" + identifier,
            data=json.dumps({"some": "data"}),
            headers={
                "Content-Type": "application/json",
                # "Accept": "application/json",
            },
            timeout=600,
        )
        self.assertEqual(response.status_code, 200)
        answer = json.loads(response.text)
        self.assertEqual(answer, {"result": "OK"})

        # return some data
        pipeline.line_ids.sorted()[-1].worker_id.return_data = True
        response = self.url_open(
            url=URL + "testing/" + identifier,
            data={"some": "data"},
            timeout=600,
        )
        self.assertEqual(response.status_code, 200)
        answer = json.loads(response.text)
        self.assertEqual(answer, {"f1": "v1"})
