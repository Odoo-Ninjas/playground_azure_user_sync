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
from odoo.addons.zbsync.tests.test_pipe import ZBSPipelineCase
from odoo.tests.common import Form
from ..models.mapping import FieldMissingException


class TestMapper(ZBSPipelineCase):
    pass

    def test_skip_record(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        initial_data = [
            {"name": "A", "line_ids": [{"product": "A"}]},
        ]

        self.env["zbs.mapping"].create(
            {
                "step_id": mapper.id,
                "field_source": "name",
                "field_dest": "f1",
                "action": "direct",
                "default_value": True,
                "skip_record_expr": "value == 'A'"
            },
        )

        instance = pipe.start(initial_data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            data._d,
            [
                {
                    "f1": "A",
                    "___default_values": ["f1"],
                    "___filter_to_delta": True,
                }
            ],
        )