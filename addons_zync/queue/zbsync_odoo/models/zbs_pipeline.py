from odoo import _, api, fields, models, SUPERUSER_ID
import json
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import odoorpc
from odoo.addons.zbsync.models.zebrooset import ZebrooSet
import pickle


class PipelineLine(models.Model):
    _inherit = "zbs.pipeline.line"

    @api.model
    def dump_data(self, data):
        # if (
        #     not isinstance(data, ZebrooSet)
        #     and not data is None
        #     and not isinstance(data, models.AbstractModel)
        # ):
        #     breakpoint()
        if isinstance(data, odoorpc.models.Model):
            connection = self.worker_id.connection_id
            data = {
                "model": data._name,
                "ids": data.ids,
                "connection_id": connection.id,
            }
            return "odoorpc:" + json.dumps(data)

        res = super().dump_data(data)
        return res

    @api.model
    def load_data(self, data):
        if isinstance(data, str) and data.startswith("odoorpc:"):
            data = json.loads(data[8:])
            conn = self.env["zbs.connection.odoo"].browse(data["connection_id"])
            instance = conn._get_obj(data["model"])
            instance = instance.browse(data["ids"])
            return instance

        res = super().load_data(data)
        return res
