from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class Proxy(models.Model):
    _name = "zbs.web.proxy"

    name = fields.Char("Name")

    protocol = fields.Selection(
        [
            ("http", "http"),
            ("https", "https"),
        ],
        string="Protocol",
    )
    url = fields.Char("URL")

    def _get_for_requests(self):
        res = {}
        for rec in self:
            res[rec.protocol] = rec.url
        return res
