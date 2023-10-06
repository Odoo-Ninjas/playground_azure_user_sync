from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from pathlib import Path
from functools import partial


class FileGrabber(models.Model):
    _inherit = ["zbs.grabber"]
    _name = "zbs.grabber.file"

    filepath = fields.Char("File Path")
    glob = fields.Char("Glob", default="*")
    recursive = fields.Boolean("Recursive")
    action_after_read = fields.Selection(
        [
            ("delete", "Delete"),
            ("move", "Move"),
        ]
    )
    destination_path = fields.Char("Destination Path")
    limit = fields.Integer("Limit Files")
    content_type = fields.Selection(
        [
            ("bytes", "Binary"),
            ("string", "Text"),
        ],
    )
    encoding = fields.Char("Encoding", default="UTF8")

    def _eval_filepath(self, record):
        return Path(self.filepath.format(record=record))

    def process_record(self, instance, index, record, data):
        path = self._eval_filepath(data)
        method = getattr(path, "rglob" if self.recursive else "glob")
        records = []
        for i, file in enumerate(method(self.glob), 1):
            if file.is_dir():
                continue
            if self.limit and i >= self.limit:
                break
            if self.content_type == "bytes":
                content = file.read_bytes()
            else:
                content = file.read_text(encoding=self.encoding)
            records.append(
                {
                    "filepath": file,
                    "filename": file.name,
                    "content": content,
                }
            )
        return records

    def process(self, instance, data):
        res = super().process(instance, data)
        records = []
        for rec in res.data:
            for x in rec:
                records.append(x)
        return instance.Result(
            records, after_commit=partial(self.after_commit, instance, records)
        )

    def after_commit(self, instance, records):
        files = [x['filepath'] for x in records]
        if self.action_after_read == "delete":
            [x.unlink() for x in files]
        elif self.action_after_read == "move":
            [x['filepath'].move(self.destination_path) for x in files]
