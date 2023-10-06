from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from requests.auth import HTTPBasicAuth
from contextlib import contextmanager
from functools import partial
from requests_oauth2client import BearerAuth
from requests_oauth2client import OAuth2Client


class WebAuth(models.Model):
    _name = "zbs.connection.web.auth"

    auth_type = fields.Selection(
        [
            ("bearer_token", "Bearer Token"),
            ("basic_auth", "Basic Auth"),
            ("oauth2", "OAuth2"),
            ("custom", "Custom"),
        ],
        string="Auth Type",
        required=True,
    )

    username = fields.Char("Username")
    password = fields.Char("Password")
    token = fields.Char("Token")
    client_id = fields.Char("Client ID")
    client_secret = fields.Char("Client Secret")
    token_endpoint = fields.Char("Token Endpoint")

    def _compute_ui_show_token(self):
        for rec in self:
            rec.ui_show_token = rec.auth_type in ["oauth2"]
            rec.ui_show_username = rec.auth_type in ["bearer_token"]

    @contextmanager
    def _do_auth(self, params):
        if self:
            self.ensure_one()

            if self.auth_type == "basic_auth":
                self._basic_auth(params)
            elif self.auth_type == "bearer_token":
                self._bearer_auth(params)
            elif self.auth_type == "oauth2_client":
                self._oauth2_client(params)
            else:
                raise NotImplementedError(self.auth_type)
        yield

    def _basic_auth(self, params):
        basic = HTTPBasicAuth(self.username, self.password)
        params["auth"] = basic

    def _bearer_auth(self, params):
        params["auth"] = BearerAuth(self.token)

    def _oauth2_client(self, params):
        params["autho"] = OAuth2Client(
            token_endpoint="https://url.to.the/token_endpoint",
            client_id="my_client_id",
            client_secret="my_client_secret",
        )
