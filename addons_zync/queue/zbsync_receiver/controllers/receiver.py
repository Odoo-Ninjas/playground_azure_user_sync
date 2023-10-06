from odoo.http import request, Controller
from odoo import http
import json
import time
import threading
from odoo.addons.zbsync.models.zebrooset import ZebrooSet

from .. import URL


class Receiver(Controller):
    @http.route(
        URL + "<identifier>",
        auth="public",
        type="http",
        method=["POST", "GET"],
        website=True,
        csrf=False,
    )
    def handler(self, identifier, **post):
        start_elements = request.env["zbs.start"].sudo()
        assert identifier
        start_elements = start_elements.search(
            [("identifier", "=", str(identifier))], limit=1, order="id desc"
        )
        if not start_elements:
            time.sleep(10)
            raise Exception("Please try again later")
        if request.httprequest.headers.get("Content-Type-orig") == "application/json":
            data = json.loads(request.httprequest.data)
        else:
            data = post

        start_elements.authorize_webrequest(
            headers=request.httprequest.headers, postdata=data, keyvalues=post
        )
        pipeline_line = (
            request.env["zbs.pipeline.line"]
            .sudo()
            .search([("worker_id", "=", f"{start_elements._name},{start_elements.id}")])
        )
        instance = pipeline_line.pipeline_id.with_context(ZBS_RAISE_ERROR=True).start(
            data
        )
        request.env.cr.commit()
        instance._start()
        instance.env.clear()
        instance.env.cr.rollback()
        if instance.state == "failed":
            # TODO decide to write debug info
            raise Exception("Error occurred")
        res = {"result": "OK"}
        if instance.next_line_id.worker_id._name == "zbs.stop":
            if instance.next_line_id.worker_id.return_data:
                res = instance._eval_data()

        if isinstance(res, (dict, list, ZebrooSet)):
            if isinstance(res, ZebrooSet):
                jsondata = res._dumps(res, env=request.env)
            else:
                jsondata = json.dumps(res)
            return http.request.make_response(
                jsondata,
                [
                    ("Content-Type", "application/json"),
                ],
            )

        else:
            return http.request.make_response(
                str(res),
                [
                    ("Content-Type", instance.next_line_id.worker_id.content_type),
                ],
            )

    @http.route(
        URL + "testing/" + "<identifier>",
        auth="public",
        type="http",
        webiste=True,
        method=["POST"],
        csrf=False,
    )
    def test_handler(self, identifier, **post):
        threading.current_thread().testing = True
        return self.handler(identifier, **post)
