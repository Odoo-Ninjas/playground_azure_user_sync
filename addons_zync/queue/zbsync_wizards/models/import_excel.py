from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ImportExcel(models.Model):
    _inherit = "zbsync.base_wizard"
    _name = "zbsync.wiz.import_excel"

    def fill_pipeline(self, pipeline):
        worker = self.env["zbs.grabber.csvexcel"].create(
            {
                "name": "-",
            }
        )
        pipeline._add_worker(worker)
