from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ZbsReceiveAuthorizer(models.Model):
    _inherit = ["mail.thread", "zbs.xport.mixin"]
    _name = "zbs.receive.authorizer"

    name = fields.Char("Name")
    code = fields.Text("Code", tracking=True)

    def authorize_webrequest(self, headers, postdata, keyvalues):
        self.ensure_one()

        if self.code:
            if not self.env['zbs.tools'].exec_get_result(self.code, {
                'headers': headers,
                'postdata': postdata,
                'keyvalues': keyvalues,
            }):
                raise Exception("Access Denied")