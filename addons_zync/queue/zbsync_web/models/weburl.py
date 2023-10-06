from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from contextlib import contextmanager
from functools import partial


class WebUrl(models.Model):
    _name = "zbs.web.url"

    name = fields.Char("URL", required=True)
    auth_id = fields.Many2one("zbs.connection.web.auth", string="Auth")
    proxy_ids = fields.Many2many("zbs.web.proxy", string="Proxies")

    @contextmanager
    def connect(self, method, params):
        params["proxies"] = self.proxy_ids._get_for_requests()
        if self.auth_id:
            with self.auth_id._do_auth(params):
                yield partial(method, **params)
        else:
            yield partial(method, **params)
