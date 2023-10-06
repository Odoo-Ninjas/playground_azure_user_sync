import requests
from contextlib import contextmanager
from xml.etree import ElementTree
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class WebEndpoint(models.Model):
    _name = "zbs.web.endpoint"

    url_id = fields.Many2one("zbs.web.url", string="URL", required=True)
    path = fields.Text("Path")
    timeout = fields.Integer("Timeout", default=10)
    request_content_type = fields.Selection(
        [
            ("application/json", "application/json"),
            ("graphql", "GraphQL Query"),
            ("form_url_encoded", "application/x-www-form-urlencoded"),
            ("html", "text/html"),
            ("xml", "application/xml"),
            ("text", "text/plain"),
        ],
        string="Request Content Type",
    )
    response_content_type = fields.Selection(
        [
            ("json", "application/json"),
            ("html", "text/html"),
            ("xml", "application/xml"),
            ("text", "text/plain"),
        ],
        string="Response Content Type",
    )
    method = fields.Selection(
        [
            ("get", "GET"),
            ("post", "POST"),
            ("put", "PUT"),
            ("patch", "PATCH"),
            ("delete", "DELETE"),
            ("head", "HEAD"),
            ("options", "OPTIONS"),
        ],
        string="Method",
        required=True,
    )

    def process(self, index, instance, data):
        with self._request(index, instance, data) as response:
            params = {
                "instance": instance,
                "index": index,
                "data": data,
                "response": response,
            }
            if self.response_content_type == "json":
                return self._process_json(**params)

            elif self.request_content_type == "xml":
                return self._process_xml(**params)
            elif self.request_content_type == "html":
                params["subtype"] = "html"
                return self._process_html(**params)
            elif self.request_content_type == "text":
                params["subtype"] = "plain"
                return self._process_html(**params)
            else:
                raise NotImplementedError(self.request_content_type)

    def _get_request_method(self):
        if not self.method:
            raise ValueError("Please define a web method!")
        meth = getattr(requests, self.method)
        return meth

    def _eval_response_state(self, response):
        response.raise_for_status()

    def _eval_path(self, index, record, data):
        self.ensure_one()
        path = (self.path or "").strip()
        instance = self.env.context.get("instance")
        _globals = instance._get_default_objects(
            {
                "index": index,
                "record": record,
                "input": data,
            }
        )
        if len(path.splitlines()) <= 1:
            path = 'f"' + path + '"'
            path = self.env["zbs.tools"].exec_get_result(path, _globals)
        else:
            path = self.env["zbs.tools"].exec_get_result(path, _globals)
        return path

    def _build_url(self, index, record, data):
        res = self.url_id.name
        if res.endswith("/"):
            res = res[:-1]
        path = self._eval_path(index, record, data)
        if not path.startswith("/"):
            path = "/" + path
        return res + path

    def _get_params(self, index, record, data):
        url = self._build_url(index, record, data)
        data = {
            "url": url,
            "timeout": self.timeout,
            "headers": self._get_headers(),
        }
        if record is not None:
            record = record._as_json()
            if self.request_content_type in ["application/json"]:
                data["json"] = record
            else:
                data["data"] = record

        return data

    def _get_headers(self):
        headers = {}
        headers["Content-Type"] = self.request_content_type
        return headers

    @contextmanager
    def _request(self, index, record, data):
        method = self._get_request_method()
        params = self._get_params(index, record, data)
        with self.url_id.connect(method, params) as callable:
            response = callable()
            self._eval_response_state(response)
            yield response

    def _process_json(self, index, instance, data, response):
        return response.json()

    def _process_xml(self, index, instance, data, response):
        tree = ElementTree.fromstring(response.content)
        return tree

    def _process_html(self, index, instance, data, response, subtype):
        res = response.text
        return res
