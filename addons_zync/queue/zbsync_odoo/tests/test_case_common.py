
from odoo.addons.zbsync.tests.test_pipe import ZBSPipelineCase


class OdooTestCase(ZBSPipelineCase):
    def _get_remote_connection(self):
        return self.env["zbs.connection.odoo"].create(
            {
                "name": "localhost",
                "port": 8069,
                "host": "localhost",
                "dbname": self.env.cr.dbname,
                "username": "admin",
                "password": "1",
            }
        )
