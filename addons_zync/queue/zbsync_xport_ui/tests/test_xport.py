import os
import pprint
import base64
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

from odoo.addons.zbsync_mapper.tests.test_mapper import TestMapper


class TestXport(TestMapper):
    def test_xport(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        self.env["zbs.mapping"].create(
            {
                "step_id": mapper.id,
                "field_source": "name",
                "field_dest": "firstname",
                "action": "direct",
                "filter_to_delta": False,
                'child_ids': [[0, 0, {
                    "field_source": "a1",
                    "field_dest": "b1",
                }]],
            }
        )
        pipe.line_ids.filtered(
            lambda x: x.worker_id._name == "zbs.start"
        ).ensure_one().sequence = 1
        pipe.line_ids.filtered(
            lambda x: x.worker_id._name == "zbs.mapper"
        ).ensure_one().sequence = 3
        pipe.line_ids.filtered(
            lambda x: x.worker_id._name == "zbs.stop"
        ).ensure_one().sequence = 4
        pipe.snapshot()
        content = pipe.version_ids[0].content.encode("utf8")
        content = base64.encodebytes(content)
        self.assertEqual(pipe.line_ids.sorted()[1].worker_id._name, "zbs.debugger")
        self.assertEqual(pipe.line_ids.sorted()[2].worker_id._name, "zbs.mapper")
        self.assertEqual(pipe.line_ids.sorted()[3].worker_id._name, "zbs.stop")
        pipe.unlink()
        wiz = self.env["zbs.import.pipeline"].create(
            {
                "filecontent": content,
            }
        )
        wiz.ok()
        pipe = pipe.search([], order="id desc", limit=1)
        self.assertTrue(pipe)
        self.assertEqual(len(pipe.line_ids), 4)
        self.assertEqual(pipe.line_ids.sorted()[1].worker_id._name, "zbs.debugger")
        self.assertEqual(pipe.line_ids.sorted()[2].worker_id._name, "zbs.mapper")
        self.assertEqual(pipe.line_ids.sorted()[3].worker_id._name, "zbs.stop")
