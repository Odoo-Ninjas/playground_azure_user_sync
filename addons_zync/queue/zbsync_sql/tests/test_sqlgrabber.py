
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


class SqlGrabber(SqlTest):

    def test_odoo_grabber(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Sql Grabber"
        pipeline = form.save()

        self.add_line(
            pipeline,
            self.env.ref("zbsync_sql.model_zbs_grabber_sql"),
            {
                "sql": (
                    "select id,name from res_partner where name ilike 'My Company'"
                ),
                "connection_id": self._get_connection().id,
            },
        )
        instance = pipeline.run_test(return_instance=True)
        instance._start(origin='test')
        for i in range(3):
            instance.heartbeat()

        data = instance._eval_data()
        self.assertEqual(data.name, "My Company")

    def test_odbc_postgres(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Sql Grabber"
        pipeline = form.save()
        self.add_line(
            pipeline,
            self.env.ref("zbsync_sql.model_zbs_grabber_sql"),
            {
                "sql": (
                    "select id,name from res_partner where name ilike 'My Company'"
                ),
                "connection_id": self._get_odbc_postgres_connection().id,
            },
        )
        instance = pipeline.run_test(return_instance=True)
        instance._start(origin='test')
        for i in range(3):
            instance.heartbeat()

        data = instance._eval_data()
        self.assertEqual(data.name, "My Company")