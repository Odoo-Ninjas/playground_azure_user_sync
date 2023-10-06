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
    def _test_odoo_grabber(self, connection, worker_settings):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Odoo Grabber"
        pipeline = form.save()

        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {
                "data": json.dumps(
                    {
                        "name": "order1",
                    }
                )
            },
        )

        settings = {
            "model": self.env.ref("zbsync_teststruct.model_zbs_test_order").model,
            "connection_id": connection.id,
        }
        settings.update(worker_settings or {})
        self.add_line(
            pipeline, self.env.ref("zbsync_odoo.model_zbs_grabber_odoo"), settings
        )
        instance = pipeline.run_test(return_instance=True)
        for i in range(3):
            instance.heartbeat()

        data = instance._eval_data()
        record = self.env["zbs.test.order"].search([])
        self.assertTrue(record)
        self.assertEqual(record.name, "order1")
        return data

    def test_odoo_grabber_local(self):
        connection = self.env.ref("zbsync_odoo.localodoo_connection")
        obj = self.env["zbs.test.order"].search([])
        obj.unlink()
        obj.create(
            {
                "name": "order1",
            }
        )
        self._test_odoo_grabber(connection, {})

    def test_odoo_grabber_remote_as_json(self):
        if os.getenv("DEVMODE") != "1":
            return
        connection = self._get_remote_connection()
        obj = self.env["zbs.test.order"].search([])
        obj.unlink()
        obj.create(
            {
                "name": "order1",
            }
        )
        self.env.cr.commit()
        self._test_odoo_grabber(connection, {})

    def test_odoo_grabber_remote_as_browse(self):
        if os.getenv("DEVMODE") != "1":
            return
        connection = self._get_remote_connection()
        obj = self.env["zbs.test.order"].search([])
        obj.unlink()
        obj.create(
            {
                "name": "order1",
            }
        )
        self.env.cr.commit()
        data = self._test_odoo_grabber(connection, {"odoo_as": "browse"})
        self.assertEqual(data.name, "order1")
