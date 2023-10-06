from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.addons.zbsync.models.zebrooset import ZebrooSet
import uuid
from pathlib import Path
from odoo.tools.safe_eval import safe_eval


class FileDumper(models.Model):
    _inherit = [
        "zbs.dumper",
    ]
    _name = "zbs.dumper.file"

    filepath = fields.Char(
        "Filepath",
        default="/tmp/a/b/{record.filename}.csv",
        help="You can use: {guid}, {any key of record})",
    )
    content_path = fields.Char("Expression to Content", help="e.g. record.content")

    def process_record(self, instance, index, record, data):
        self = self.with_context(instance=instance)

        vars = {
            "guid": str(uuid.uuid4()),
            "record": record,
        }
        filepath = Path(self.filepath.format(**vars))
        content = self.env['zbs.tools'].exec_get_result(
            self.content_path, {'record': record, 'data': data})

        if isinstance(content, str):
            filepath.write_text(record.content)
        elif isinstance(content, bytes):
            filepath.write_bytes(record.content)
        else:
            raise NotImplementedError(content)
        return {"filepath": filepath, "record": record}
