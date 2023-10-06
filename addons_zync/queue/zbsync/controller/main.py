from odoo import http
from odoo.http import request
from odoo.http import content_disposition


class Main(http.Controller):
    @http.route("/zync_download/<id>", auth="user", type="http")
    def handler(self, id, **post):
        version = request.env["zbs.pipeline.version"].browse(int(id))
        content = version.content
        name = f"{version.pipeline_id.name}.{version.date}.json"
        return http.request.make_response(
            content,
            [
                ("Content-Type", "application/json"),
                ("Content-Disposition", f'attachment; filename="{name}"'),
            ],
        )
