from pathlib import Path
import os
import json
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


class TestMapper(ZBSPipelineCase):
    def test_xport(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = {
            "name": "testpartner1",
        }

        self.env["zbs.mapping"].create(
            {
                "step_id": mapper.id,
                "field_source": "name",
                "field_dest": "firstname",
                "action": "direct",
                "filter_to_delta": False,
            }
        )

        data = pipe.dump()

        pipe.unlink()
        self.env["zbs.mapping"].search([]).unlink()
        self.assertFalse(self.env["zbs.mapping"].search([]))

        pipe = self.env["zbs.pipeline"].load(data)

        self.assertTrue(self.env["zbs.mapping"].search([]))
