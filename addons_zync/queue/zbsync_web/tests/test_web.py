import os
import pprint
import logging
import time
import json
import uuid
from datetime import datetime, timedelta
from unittest import skipIf
from odoo import api
from odoo import fields
from odoo.tests.common import TransactionCase, Form
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, RedirectWarning, ValidationError, AccessError
from odoo.addons.zbsync.tests.test_pipe import ZBSPipelineCase


class Unittest(ZBSPipelineCase):
    def test_webworker_(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Webworker"
        pipeline = form.save()

        model = self.env.ref("zbsync.model_zbs_const")
        _, pipeline_line = self.add_line(
            pipeline, model, {"data": json.dumps({"intA": 100, "intB": 200})}
        )
        url = self.env["zbs.web.url"].create({"name": "http://www.dneonline.com"})
        endpoint = self.env["zbs.web.endpoint"].create(
            {
                "url_id": url.id,
                "path": "/calculator.asmx",
                "method": "get",
                "request_content_type": "html",
                "response_content_type": "html",
            }
        )
        pipeline_line.path_content = "data"
        model = self.env.ref("zbsync_web.model_zbs_web_worker")
        webworker, _ = self.add_line(pipeline, model, {"endpoint_id": endpoint.id})

        instance = pipeline.run_test(return_instance=True)
        for i in range(3):
            instance.heartbeat()
        test = instance._eval_data()
        self.assertTrue("<html>" in test[0])
