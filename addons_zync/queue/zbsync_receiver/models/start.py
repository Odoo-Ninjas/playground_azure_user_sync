from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import uuid
from .. import URL


class StartElement(models.Model):
    _inherit = "zbs.start"

    url = fields.Char("URL", compute="_compute_url")
    identifier = fields.Char("Identifier")
    authorizer_id = fields.Many2one("zbs.receive.authorizer", "Authorizer")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['identifier'] = '/get_something'
        return res

    @api.depends("identifier")
    def _compute_url(self):
        for rec in self:
            url = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(key="web.base.url", default=False)
            )
            url += URL + rec.identifier
            rec.url = url

    def authorize_webrequest(self, headers, postdata, keyvalues):
        self.ensure_one()
        if not self.authorizer_id:
            return True

        self.authorizer_id.authorize_webrequest(headers, postdata, keyvalues)