import os
from odoo.addons.zbsync_odoo.tests.test_odoo_grabber import OdooDumper
from odoo.addons.zbsync_mapper.tests.test_mapper import TestMapper
from odoo.addons.zbsync.models.zebrooset import ZebrooSet


class TestDumperMapper(OdooDumper, TestMapper):
    def test_mapping_odoorpc(self):
        if os.getenv("DEVMODE") != "1":
            return
        connection = self._get_remote_connection()
        obj = self.env["zbs.test.order"].search([])
        obj.unlink()
        obj.create(
            {
                "name": "order1",
            }
        )

        self.env.cr.commit()
        data = self._test_odoo_grabber(connection, {"odoo_as": "browse"})
        self.assertEqual(data.name, "order1")
        pipeline = self.env["zbs.pipeline"].search([], order="id desc", limit=1)
        mapper = self.env["zbs.mapper"].create({})
        pipeline.line_ids = [[0, 0, {"worker_id": f"{mapper._name},{mapper.id}"}]]

        self.env["zbs.mapping"].create(
            {
                "step_id": mapper.id,
                "field_source": "name",
                "field_dest": "ordername",
                "action": "direct",
                "filter_to_delta": False,
            }
        )
        pipeline.line_ids.filtered(lambda x: x.worker_id._name == 'zbs.mapper').sequence= 500
        pipeline.line_ids.filtered(lambda x: x.worker_id._name == 'zbs.stop').sequence= 10000
        for line in pipeline.line_ids.sorted():
            print(f"{line.worker_id._name}: {line.sequence}")
        self.assertEqual(pipeline.line_ids.sorted()[-2].worker_id._name, "zbs.mapper")
        instance = pipeline.run_test(return_instance=True)
        for i in range(4):
            instance.heartbeat()
        data = instance._eval_data()
        self.assertTrue(isinstance(data, ZebrooSet))
        self.assertEqual(data.ordername, "order1")
