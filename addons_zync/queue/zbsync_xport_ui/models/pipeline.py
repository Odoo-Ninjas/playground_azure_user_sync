import tempfile
import os
import zipfile
from pathlib import Path

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class Pipeline(models.Model):
    _inherit = "zbs.pipeline"

    def _get_zipped_json(self):
        self.snapshot()

        parent_dir = Path(tempfile.mktemp(suffix=""))
        parent_dir.mkdir(exist_ok=True, parents=True)
        filename = ",".join(sorted(map(str, self.ids))) + ".zip"
        zipfile_path = parent_dir / filename
        os.chdir(parent_dir)

        with zipfile.ZipFile(zipfile_path, mode='w') as zipf:
            for rec in self:
                version = rec.version_ids.sorted()[0]
                content = version.content
                date = version.date.strftime("%Y%m%d_%H%M%S")
                file = parent_dir / f"{rec.id}-{rec.name}-{date}.json"
                file.write_text(content)
                zipf.write(file.name)
        return zipfile_path.read_bytes()

    def download(self):
        ids = self.ids
        str_ids = ','.join(map(str, ids))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/zync/download?ids={str_ids}',
            'target': 'self'
        }