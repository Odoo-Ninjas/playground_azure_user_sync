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
from odoo.addons.zbsync.tests.test_pipe import ZBSPipelineCase
from pathlib import Path


class FileDumper(ZBSPipelineCase):
    def test_file_dumper(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "File Dumper"
        pipeline = form.save()
        guid = str(uuid.uuid4())
        path = Path(f"/tmp/{guid}")
        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {
                "data": json.dumps(
                    [
                        {
                            "name": 'myname1',
                            'content': 'anton',
                        },
                    ]
                ),
            },
        )
        _, pipeline_line = self.add_line(
            pipeline,
            self.env.ref("zbsync_files.model_zbs_dumper_file"),
            {
                "filepath": str(path) + "/{record.name}.csv",
                "content_path": "record.content",
            },
        )

        instance = pipeline.run_test(return_instance=True)
        instance._start(origin="test")

        path.mkdir(exist_ok=True)
        for i in range(3):
            instance.heartbeat()

        file1 = path / 'myname1.csv'
        data = instance._eval_data()
        self.assertEqual(data.record.name, "myname1")
        self.assertTrue(file1.exists())
        self.assertEqual((path / 'myname1.csv').read_text().strip(), 'anton')
