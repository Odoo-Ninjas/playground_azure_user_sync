import json
import os
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
from odoo.tests import Form
from odoo.addons.zbsync.tests.test_pipe import ZBSPipelineCase


class SoapTest(ZBSPipelineCase):
    def test_soap(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Soap-Test"
        pipeline = form.save()

        model = self.env.ref("zbsync.model_zbs_const")
        _, pipeline_line = self.add_line(
            pipeline, model, {"data": json.dumps({"intA": 100, "intB": 200})}
        )
        pipeline_line.path_content = "data"
        model = self.env.ref("zbsync_soap.model_zbs_grabber_soap")
        soap_grabber, _ = self.add_line(
            pipeline, model, {"function_call": "Add(**record)"}
        )

        soap_grabber.connection_id = self.env["zbs.connection.soap"].create(
            {"wsdl_url": "http://www.dneonline.com/calculator.asmx?wsdl"}
        )
        instance = pipeline.run_test(return_instance=True)
        for i in range(3):
            instance.heartbeat()
        test = instance._eval_data()
        self.assertEqual(test[0], 300)
