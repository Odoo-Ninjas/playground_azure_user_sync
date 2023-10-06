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
from pathlib import Path
from odoo.addons.zbsync.tests.test_pipe import ZBSPipelineCase


class TestCsvExcel(ZBSPipelineCase):
    def test_grabber_csv(self):
        Path("/tmp/test.csv").write_text(("name1;street\n" "Hans;Ringstr.\n"))

    def test_import_csv(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "File Grabber"
        pipeline = form.save()
        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps([{"content": ("Name;Street\n" "john doe;street1")}])},
        )
        _, pipeline_line = self.add_line(
            pipeline,
            self.env.ref("zbsync_excel_csv.model_zbs_grabber_csvexcel"),
            {
                "type": "csv",
                "csv_delimiter": ";",
            },
        )
        pipeline_line.path_content = "data.content"

        instance = pipeline.run_test(return_instance=True)
        instance._start(origin="test")

        for i in range(3):
            instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(data.Name, "john doe")
        self.assertEqual(data.Street, "street1")

    def test_import_csv_bytes(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "File Grabber"
        pipeline = form.save()
        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {
                "data": json.dumps(
                    [{"content": ("Name;Street\n" "john doe;street1")}]
                ).encode("utf8")
            },
        )
        _, pipeline_line = self.add_line(
            pipeline,
            self.env.ref("zbsync_excel_csv.model_zbs_grabber_csvexcel"),
            {
                "type": "csv",
                "csv_delimiter": ";",
            },
        )
        pipeline_line.path_content = "data.content"

        instance = pipeline.run_test(return_instance=True)
        instance._start(origin="test")

        for i in range(3):
            instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(data.Name, "john doe")
        self.assertEqual(data.Street, "street1")

    def test_export_csv(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Dumper"
        pipeline = form.save()
        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {
                "data": json.dumps(
                    [
                        {"name": "johnny"},
                    ]
                ),
            },
        )
        _, pipeline_line = self.add_line(
            pipeline,
            self.env.ref("zbsync_excel_csv.model_zbs_dumper_csvexcel"),
            {
                "type": "csv",
                "csv_delimiter": ";",
            },
        )
        pipeline_line.path_content = "data.content"

        instance = pipeline.run_test(return_instance=True)
        instance._start(origin="test")

        for i in range(3):
            instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(data.content, "name\r\njohnny\r\n"),
        self.assertTrue(isinstance(data.content, str))

    def test_export_excel(self):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Dumper"
        pipeline = form.save()
        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {
                "data": json.dumps(
                    [
                        {"name": "johnny"},
                    ]
                ),
            },
        )
        _, pipeline_line = self.add_line(
            pipeline,
            self.env.ref("zbsync_excel_csv.model_zbs_dumper_csvexcel"),
            {
                "type": "excel",
            },
        )
        pipeline_line.path_content = "data.content"

        instance = pipeline.run_test(return_instance=True)
        instance._start(origin="test")

        for i in range(3):
            instance.heartbeat()
        data = instance._eval_data()
        self.assertTrue(isinstance(data.content, bytes))

        guid = str(uuid.uuid4())
        file = Path(f"/tmp/{guid}/file.xlsx")
        file.parent.mkdir(exist_ok=True, parents=True)
        file.write_bytes(data.content)

        form = Form(self.env["zbs.pipeline"])
        form.name = "Grabber"
        pipeline = form.save()
        self.add_line(
            pipeline,
            self.env.ref("zbsync_files.model_zbs_grabber_file"),
            {
                "filepath": str(file.parent),
                "glob": file.name,
                "content_type": "bytes",
            },
        )
        _, pipeline_line = self.add_line(
            pipeline,
            self.env.ref("zbsync_excel_csv.model_zbs_grabber_csvexcel"),
            {
                "type": "excel",
            },
        )
        pipeline_line.path_content = "data.content"
        instance = pipeline.run_test(return_instance=True)
        instance._start(origin="test")

        for i in range(3):
            instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(data.name, "johnny")
