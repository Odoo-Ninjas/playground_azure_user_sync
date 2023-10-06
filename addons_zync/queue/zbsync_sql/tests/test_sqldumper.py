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
from .common import SqlTest


class SqlDumper(SqlTest):
    def test_sql_dumper(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Sql Dumper"
        pipeline = form.save()
        guid = str(uuid.uuid4())
        const_worker, _ = self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {
                "data": json.dumps(
                    [
                        {
                            "name": guid,
                            "___keys": ["name"],
                        },
                        {
                            "name": guid + "-2",
                            "___keys": ["name"],
                        },
                    ]
                ),
            },
        )

        self.add_line(
            pipeline,
            self.env.ref("zbsync_sql.model_zbs_dumper_sql"),
            {
                "table": "zbs_test_partner",
                "connection_id": self._get_connection().id,
            },
        )

        instance = pipeline.run_test(return_instance=True)
        instance._start(origin="test")
        for i in range(3):
            instance.heartbeat()

        data = instance._eval_data()
        self.assertEqual(data["create"][0]["name"], guid)
        self.assertEqual(data["create"][1]["name"], guid + "-2")

        # update record in sql
        const_worker.data = json.dumps(
            [
                {
                    "name": guid,
                    "___keys": ["name"],
                },
                {
                    "name": guid + "-2",
                    "___keys": ["name"],
                },
            ]
        )

        instance = pipeline.run_test(return_instance=True)
        instance._start(origin="test")
        for i in range(3):
            instance.heartbeat()

        data = instance._eval_data()
        self.assertEqual(data["update"][0]["name"], guid)
        self.assertEqual(data["update"][1]["name"], guid + "-2")