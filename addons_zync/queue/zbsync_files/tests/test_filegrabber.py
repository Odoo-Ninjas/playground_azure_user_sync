from passlib.context import CryptContext
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
from pathlib import Path


class FileGrabber(ZBSPipelineCase):
    def test_file_grabber(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "File Grabber"
        pipeline = form.save()
        guid = str(uuid.uuid4())
        path = Path(f"/tmp/{guid}")
        file_grabber = self.add_line(
            pipeline,
            self.env.ref("zbsync_files.model_zbs_grabber_file"),
            {
                "filepath": str(path),
                "glob": "*.csv",
                "recursive": False,
                "action_after_read": "delete",
                "content_type": "string",
            },
        )

        instance = pipeline.run_test(return_instance=True)
        instance._start(origin="test")

        path.mkdir(exist_ok=True)
        file1 = path / "file1.csv"
        file1.write_text("here i am")
        for i in range(3):
            instance.heartbeat()
        self.assertTrue(not file1.exists())

        data = instance._eval_data()
        self.assertEqual(data.filename, "file1.csv")
