from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools.safe_eval import safe_eval
import zeep


class CustomTransport(zeep.Transport):
    pass


class SoapGrabber(models.Model):
    _inherit = "zbs.grabber"
    _name = "zbs.grabber.soap"

    connection_id = fields.Many2one("zbs.connection.soap", required=False)
    content_path = fields.Char("Content Path")
    function_call = fields.Char(
        "Call",
        default="ConvertSpeed(100, 'kilometersPerhour', 'milesPerhour')",
        help="Use data.value xyz to access the data",
    )
    timeout = fields.Integer("Timeout")

    def process_record(self, instance, index, record, data):
        objects = instance._get_default_objects({"record": record})
        func_call = self.function_call.format(**objects)

        if self.content_path:
            data = safe_eval(self.content_path, {"record": record})
        else:
            data = {}

        session = self.connection_id._create_session()
        transport = CustomTransport(
            session=session,
            timeout=self.timeout or None,
        )
        client = zeep.Client(
            wsdl=self.connection_id.wsdl_url,
            transport=transport,
        )
        result = None
        objects.update({"data": data, "client": client, "result": result})
        result = self.env["zbs.tools"].exec_get_result(
            "client.service." + func_call,
            objects,
        )
        return result
