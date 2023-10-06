# used to watch the intermediate results
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import logging


class ZBSDebugger(models.Model):
    _inherit = "zbs.worker"
    _name = "zbs.debugger"
    _description = "debug"

    def process(self, instance, data):
        logger = logging.getLogger(f"zbs.debugger")
        for index, record in self._iterate_data(data):
            logger.info(str(record))
        return instance.Result(data)
