import arrow
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


class TestExcelCSV(TransactionCase):
    def setUp(self):
        super().setUp()

    def test_excel_csv_wizard(self):
        form = Form(self.env["zbsync.import_excel"])
        form.fill_pipeline()
        pipeline = form.save()
        self.assertTrue(
            pipeline.line_ids.filtered(
                lambda x: x.worker_id._name == "zbs.grabber.csvexcel"
            )
        )
