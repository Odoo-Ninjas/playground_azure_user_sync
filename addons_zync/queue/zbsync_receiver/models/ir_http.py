from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo import http
from .. import URL


class HttpRoot(http.Root):
    def get_request(self, httprequest):
        if httprequest.path.startswith(URL):
            return ZSyncRequest(httprequest)
        return super(HttpRoot, self).get_request(httprequest)


class ZSyncRequest(http.HttpRequest):
    def dispatch(self):
        headers = dict(self.httprequest.headers)
        if headers.get("Content-Type") == "application/json":
            headers["Content-Type"] = "text/json"
            headers["Content-Type-orig"] = "application/json"
            self.httprequest.headers = headers
        res = super(ZSyncRequest, self).dispatch()
        return res


http.Root = HttpRoot
http.root = HttpRoot()
