import base64
from odoo import http
from odoo.http import request
from odoo.http import content_disposition


class Controller(http.Controller):

    @http.route('/zync/download', auth='user', type="http")
    def download_flows(self, **post):
        str_ids = post['ids']
        ids = map(int, str_ids.split(','))
        pipes = request.env['zbs.pipeline'].browse(ids)
        pipes.snapshot()
        zip = pipes._get_zipped_json()
        filename = f'pipes_{str_ids}.zip'
        return http.request.make_response(zip, [
            ('Content-Type', 'application/octet-stream; charset=binary'),
            ('Content-Disposition', content_disposition(filename))
        ])

