import os
from passlib.context import CryptContext
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
from .test_case_common import OdooTestCase


class OdooDumper(OdooTestCase):
    def _test_odoo_dumper(
        self, connection, data, model="zbsync_teststruct.model_zbs_test_order"
    ):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Hansi"
        pipeline = form.save()

        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps(data)},
        )

        self.add_line(
            pipeline,
            self.env.ref("zbsync_odoo.model_zbs_dumper_odoo"),
            {
                "model": self.env.ref(model).model,
                "connection_id": connection.id,
            },
        )
        instance = pipeline.run_test(return_instance=True)
        for i in range(3):
            instance.heartbeat()

        data = instance._eval_data()
        record = self.env[self.env.ref(model).model].search([])
        return record, data
