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
    def test_mappings_simple_direct(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = self.env.user

        self.env["zbs.mapping"].create(
            {
                "step_id": mapper.id,
                "field_source": "name",
                "field_dest": "n1",
                "action": "direct",
                "filter_to_delta": False,
            }
        )
        self.env["zbs.mapping"].create(
            {
                "step_id": mapper.id,
                "field_source": "partner_id.name",
                "field_dest": "partner_name",
                "action": "direct",
                "filter_to_delta": False,
            }
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(str(data._d), "[{'n1': 'OdooBot', 'partner_name': 'OdooBot'}]")

    def test_mappings_m2m_field(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        order = self.env["zbs.test.order"].create(
            {
                "name": "order1",
                "tag_ids": [
                    [
                        0,
                        0,
                        {
                            "name": "tag1",
                        },
                    ],
                    [
                        0,
                        0,
                        {
                            "name": "tag2",
                        },
                    ],
                ],
            }
        )
        self.env["zbs.mapping"].create(
            {
                "step_id": mapper.id,
                "field_source": "tag_ids",
                "field_dest": "tags",
                "action": "list",
                "filter_to_delta": False,
                "child_ids": [
                    [
                        0,
                        0,
                        {
                            "field_source": "",
                            "field_dest": "",
                            "action": "object",
                            "filter_to_delta": False,
                            "child_ids": [
                                [
                                    0,
                                    0,
                                    {
                                        "field_source": "name",
                                        "field_dest": "n1",
                                        "action": "direct",
                                        "filter_to_delta": False,
                                    },
                                ]
                            ],
                        },
                    ]
                ],
            }
        )

        instance = pipe.start(order)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(str(data._d), "[{'tags': [{'n1': 'tag1'}, {'n1': 'tag2'}]}]")
