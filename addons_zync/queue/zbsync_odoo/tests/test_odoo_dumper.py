import os
from passlib.context import CryptContext
import json
import os
import pprint
import logging
import time
import uuid
from datetime import datetime, timedelta
from unittest import skipIf
from odoo import api
from odoo import fields
from odoo.tests.common import TransactionCase, Form
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, RedirectWarning, ValidationError, AccessError
from .test_case_common import OdooTestCase


class OdooDumper(OdooTestCase):
    def _test_odoo_dumper(
        self, connection, data, model="zbsync_teststruct.model_zbs_test_order"
    ):
        form = Form(self.env["zbs.pipeline"])
        form.name = "Hansi"
        pipeline = form.save()

        self.add_line(
            pipeline,
            self.env.ref("zbsync.model_zbs_const"),
            {"data": json.dumps(data)},
        )

        self.add_line(
            pipeline,
            self.env.ref("zbsync_odoo.model_zbs_dumper_odoo"),
            {
                "model": self.env.ref(model).model,
                "connection_id": connection.id,
            },
        )
        instance = pipeline.run_test(return_instance=True)
        for i in range(3):
            instance.heartbeat()

        data = instance._eval_data()
        record = self.env[self.env.ref(model).model].search([])
        return record, data

    def test_m2o_with_id(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.partner"].search([]).unlink()
            partner1 = self.env["zbs.test.partner"].create({"name": "hans"})
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = {
                "name": "testpartner1",
                "partner_id": partner1.id,
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "testpartner1")
                self.assertEqual(record.partner_id.name, "hans")
                self.assertTrue(isinstance(data.created[0].id, int))
            else:
                self.assertTrue(data.created)

    def test_m2o_keyresolve(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.partner"].search([]).unlink()
            partner1 = self.env["zbs.test.partner"].create({"name": "hans"})
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = {
                "name": "testpartner1",
                "partner_id": {
                    "___keys": ["name"],
                    "name": "hans",
                },
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "testpartner1")
                self.assertEqual(record.partner_id.name, "hans")
                self.assertEqual(partner1.search_count([]), 1)
                self.assertTrue(isinstance(data.created[0].id, int))
            else:
                self.assertTrue(data.created)
                obj = connection._get_obj(partner1._name)
                self.assertEqual(len(obj.search([("name", "=", "hans")])), 1)

    def test_m2o_keyresolve_two_levels(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.partner"].search([]).unlink()
            partner1 = self.env["zbs.test.partner"].create({"name": "hans"})
            if not connection.is_local_connection:
                self.env.cr.commit()
                obj = connection._get_obj(partner1._name)
                partner = obj.search([("name", "=", "hans")])
                self.assertEqual(len(partner), 1)
                partner = obj.browse(partner[0])
                self.assertFalse(partner.parent_partner_id)
            data = {
                "name": "testpartner1",
                "partner_id": {
                    "___keys": ["name"],
                    "name": "hans",
                    "parent_partner_id": {
                        "___keys": ["name"],
                        "name": "hans",
                    },
                },
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "testpartner1")
                self.assertEqual(record.partner_id.name, "hans")
                self.assertEqual(partner1.search_count([]), 1)
                self.assertTrue(isinstance(data.created[0].id, int))
            else:
                self.assertTrue(data.created)
                obj = connection._get_obj(partner1._name)
                partner = obj.search([("name", "=", "hans")])
                self.assertEqual(len(partner), 1)
                partner = obj.browse(partner[0])
                self.assertEqual(partner[0].parent_partner_id.name, "hans")

    def test_one2many(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.order.line"].search([]).unlink()
            # force use of parent key to identify
            self.env["zbs.test.order.line"].create(
                [
                    {"name": "product1"},
                    {"name": "product2"},
                ]
            )
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = {
                "name": "order1",
                "line_ids": [
                    {"name": "product1", "___keys": ["name"]},
                    {"name": "product2", "___keys": ["name"]},
                ],
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertEqual(record.line_ids[0].name, "product1")
                self.assertEqual(record.line_ids[1].name, "product2")
                self.assertTrue(isinstance(data.created[0].id, int))
            else:
                self.assertTrue(data.created)

            data = {
                "name": "order1",
                "___keys": ["name"],
                "line_ids": [
                    {"name": "product1", "___keys": ["name"], "anyfield": "abc"},
                ],
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertEqual(record.line_ids[0].name, "product1")
                self.assertEqual(record.line_ids[0].anyfield, "abc")
                self.assertEqual(len(record.line_ids), 2)
            else:
                self.assertTrue(data.updated)

            # test unlink
            data = {
                "name": "order1",
                "___keys": ["name"],
                "___keys_delete": ["line_ids"],
                "line_ids": [
                    {
                        "name": "product1",
                        "anyfield": "abcd",
                        "___keys": ["name"],
                    },
                ],
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertEqual(record.line_ids[0].name, "product1")
                self.assertEqual(record.line_ids[0].anyfield, "abcd")
                self.assertEqual(len(record.line_ids), 1)
            else:
                self.assertTrue(data.updated)

    def test_many2many(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.tag"].search([]).unlink()
            # force use of parent key to identify
            self.env["zbs.test.tag"].create(
                [
                    {"name": "tag1"},
                ]
            )
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = {
                "name": "order1",
                "___keys": ["name"],
                "tag_ids": [{"name": "tag1", "anyfield": "v1", "___keys": ["name"]}],
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertEqual(record.tag_ids.name, "tag1")
                self.assertEqual(record.tag_ids.anyfield, "v1")
                self.assertEqual(record.tag_ids.search_count([]), 1)
                self.assertTrue(isinstance(data.created[0].id, int))
            else:
                self.assertTrue(data.created)

            data = {
                "name": "order1",
                "___keys": ["name"],
                "tag_ids": [{"name": "tag2", "anyfield": "v2", "___keys": ["name"]}],
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertIn("tag1", record.tag_ids.mapped("name"))
                self.assertIn("tag2", record.tag_ids.mapped("name"))
                self.assertIn("v1", record.tag_ids.mapped("anyfield"))
                self.assertIn("v2", record.tag_ids.mapped("anyfield"))
                self.assertEqual(record.tag_ids.search_count([]), 2)
            else:
                self.assertTrue(data.updated)

            # test unlink (remove from record)
            data = {
                "name": "order1",
                "___keys": ["name"],
                "___keys_delete": ["tag_ids"],
                "tag_ids": [{"name": "tag1", "___keys": ["name"]}],
            }

            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertIn("tag1", record.tag_ids.mapped("name"))
                self.assertNotIn("tag2", record.tag_ids.mapped("name"))
                self.assertIn("v1", record.tag_ids.mapped("anyfield"))
                self.assertNotIn("v2", record.tag_ids.mapped("anyfield"))
                self.assertEqual(record.tag_ids.search_count([]), 2)
            else:
                self.assertTrue(data.updated)


    def test_default_value_and_filter_data_to_delta(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.tag"].search([]).unlink()
            self.env["zbs.test.tag"].create(
                [
                    {"name": "tag1"},
                ]
            )
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = {
                "name": "order1",
                "___keys": ["name"],
                "tag_ids": [{"name": "tag1", "anyfield": "v1", "___keys": ["name"]}],
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertEqual(record.tag_ids.name, "tag1")
                self.assertEqual(record.tag_ids.anyfield, "v1")
                self.assertEqual(record.tag_ids.search_count([]), 1)
                self.assertTrue(isinstance(data.created[0].id, int))
            else:
                self.assertTrue(data.created)

    def test_default_value(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.tag"].search([]).unlink()
            self.env["zbs.test.tag"].create(
                [
                    {"name": "tag1", "anyfield": "v1"},
                ]
            )
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = {
                "name": "tag1",
                "anyfield": "v2",
                "___default_values": ["anyfield"],
                "___keys": ["name"],
            }
            record, data = self._test_odoo_dumper(
                connection, data, model="zbsync_teststruct.model_zbs_test_tag"
            )
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "tag1")
                self.assertEqual(record.anyfield, "v1")
                self.assertTrue(isinstance(data.updated[0][0], int))
            else:
                self.assertTrue(data.updated)

    def test_filter_delta_values(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.tag"].search([]).unlink()
            self.env["zbs.test.tag"].create(
                [
                    {"name": "tag1", "anyfield": "v1"},
                ]
            )
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = {
                "name": "tag1",
                "anyfield": "v2",
                "___filter_to_delta": True,
                "___keys": ["name"],
            }
            record, data = self._test_odoo_dumper(
                connection, data, model="zbsync_teststruct.model_zbs_test_tag"
            )
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "tag1")
                self.assertEqual(record.anyfield, "v2")
                self.assertTrue(isinstance(data.updated[0][0], int))
            else:
                self.assertTrue(data.updated)

    def test_dump_if_idcolumn_set(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.tag"].search([]).unlink()
            tag = self.env["zbs.test.tag"].create(
                [
                    {"name": "tag1", "anyfield": "v1"},
                ]
            )
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = {
                "name": "tag2",
                "id": tag.id,
            }
            record, data = self._test_odoo_dumper(
                connection, data, model="zbsync_teststruct.model_zbs_test_tag"
            )
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "tag2")
                self.assertEqual(record.anyfield, "v1")
                self.assertTrue(isinstance(data.updated[0][0], int))
            else:
                self.assertTrue(data.updated)

    def test_many2one(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = {
                "name": "order1",
                "line_ids": [
                    {"name": "product1", "___keys": ["name"]},
                    {"name": "product2", "___keys": ["name"]},
                ],
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertEqual(record.line_ids[0].name, "product1")
                self.assertEqual(record.line_ids[1].name, "product2")
                self.assertTrue(isinstance(data.created[0].id, int))
            else:
                self.assertTrue(data.created)

            data = {
                "name": "order1",
                "___keys": ["name"],
                "line_ids": [
                    {"name": "product1", "___keys": ["name"], "anyfield": "abc"},
                ],
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertEqual(record.line_ids[0].name, "product1")
                self.assertEqual(record.line_ids[0].anyfield, "abc")
                self.assertEqual(len(record.line_ids), 2)
            else:
                self.assertTrue(data.updated)

            # test unlink
            data = {
                "name": "order1",
                "___keys": ["name"],
                "___keys_delete": ["line_ids"],
                "line_ids": [
                    {
                        "name": "product1",
                        "anyfield": "abcd",
                        "___keys": ["name"],
                    },
                ],
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertEqual(record.line_ids[0].name, "product1")
                self.assertEqual(record.line_ids[0].anyfield, "abcd")
                self.assertEqual(len(record.line_ids), 1)
            else:
                self.assertTrue(data.updated)

    def test_many2one_no_keys(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.partner"].search([]).unlink()
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = [{"name": "hans", "parent_partner_id": "meike"}]
            record, data = self._test_odoo_dumper(
                connection, data, model="zbsync_teststruct.model_zbs_test_partner"
            )
            record = record.filtered(lambda r: r.name == "hans")
            if connection.is_local_connection:
                self.assertEqual(len(record), 1)
                self.assertTrue(record)
                self.assertEqual(record.name, "hans")
                self.assertEqual(record.parent_partner_id.name, "meike")
                self.assertTrue(isinstance(data.created[0].id, int))
            else:
                self.assertTrue(data.created)
                partner = connection._get_obj("zbs.test.partner")
                res = partner.search([("name", "=", "hans")])
                self.assertEqual(len(res), 1)

                res = partner.search([("name", "=", "meike")])
                self.assertEqual(len(res), 1)

            data = {
                "name": "hans2",
                "parent_partner_id": "meike",
            }
            record, data = self._test_odoo_dumper(
                connection, data, model="zbsync_teststruct.model_zbs_test_partner"
            )
            record = record.filtered(lambda r: r.name == "hans2")
            if connection.is_local_connection:
                self.assertEqual(len(record), 1)
                self.assertTrue(record)
                self.assertEqual(record.name, "hans2")
                self.assertEqual(record.parent_partner_id.name, "meike")
            else:
                self.assertTrue(data.created)
                partner = connection._get_obj("zbs.test.partner")
                res = partner.search([("name", "=", "hans2")])
                self.assertEqual(len(res), 1)

                res = partner.search([("name", "=", "meike")])
                self.assertEqual(len(res), 1)

    def test_many2many_just_ids(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.tag"].search([]).unlink()
            # force use of parent key to identify
            tag1 = self.env["zbs.test.tag"].create(
                [
                    {"name": "tag1"},
                ]
            )
            if not connection.is_local_connection:
                self.env.cr.commit()
            data = {
                "name": "order1",
                "___keys": ["name"],
                "tag_ids": [tag1.id],
            }
            record, data = self._test_odoo_dumper(connection, data)
            if connection.is_local_connection:
                self.assertTrue(record)
                self.assertEqual(record.name, "order1")
                self.assertEqual(record.tag_ids.name, "tag1")
                self.assertEqual(record.tag_ids.search_count([]), 1)
                self.assertTrue(isinstance(data.created[0].id, int))
            else:
                self.assertTrue(data.created)

    def test_many2many_with_odoorecords(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.tag"].search([]).unlink()
            # force use of parent key to identify
            tag1 = self.env["zbs.test.tag"].create({"name": "tag1"})
            tag2 = self.env["zbs.test.tag"].create({"name": "tag2"})
            if not connection.is_local_connection:
                self.env.cr.commit()

            data = {
                "name": "order1",
                "___keys": ["name"],
                "tag_ids": [
                    {
                        "_type": "odoo_recordset",
                        "model": tag1._name,
                        "ids": tag1.ids,
                        "uid": self.env.uid,
                        "su": False,
                        "context": {},
                    },
                ],
            }
            if not connection.is_local_connection:
                # just test for error
                with self.assertRaises(ValidationError):
                    record, data = self._test_odoo_dumper(connection, data)
            else:
                record, data = self._test_odoo_dumper(connection, data)
                if connection.is_local_connection:
                    self.assertTrue(record)
                    self.assertEqual(record.name, "order1")
                    self.assertEqual(record.tag_ids.name, "tag1")
                    self.assertEqual(record.tag_ids.search_count([]), 2)
                    self.assertTrue(isinstance(data.created[0].id, int))
                else:
                    self.assertTrue(data.created)

                data = {
                    "name": "order1",
                    "___keys": ["name"],
                    "tag_ids": [
                        {
                            "_type": "odoo_recordset",
                            "model": tag1._name,
                            "ids": tag1.ids + tag2.ids,
                            "uid": self.env.uid,
                            "su": False,
                            "context": {},
                        }
                    ],
                }
                record, data = self._test_odoo_dumper(connection, data)
                if connection.is_local_connection:
                    self.assertTrue(record)
                    self.assertEqual(record.name, "order1")
                    self.assertIn("tag1", record.tag_ids.mapped("name"))
                    self.assertIn("tag2", record.tag_ids.mapped("name"))
                    self.assertEqual(record.tag_ids.search_count([]), 2)
                else:
                    self.assertTrue(data.updated)

                # test unlink (remove from record)
                data = {
                    "name": "order1",
                    "___keys": ["name"],
                    "___keys_delete": ["tag_ids"],
                    "tag_ids": [
                        {
                            "_type": "odoo_recordset",
                            "model": tag1._name,
                            "ids": tag1.ids,
                            "uid": self.env.uid,
                            "su": False,
                            "context": {},
                        },
                    ],
                }

                record, data = self._test_odoo_dumper(connection, data)
                if connection.is_local_connection:
                    self.assertTrue(record)
                    self.assertEqual(record.name, "order1")
                    self.assertIn("tag1", record.tag_ids.mapped("name"))
                    self.assertNotIn("tag2", record.tag_ids.mapped("name"))
                    self.assertEqual(record.tag_ids.search_count([]), 2)
                else:
                    self.assertTrue(data.updated)

    def test_many2many_with_odoorecords(self):
        for connection in [
            self.env.ref("zbsync_odoo.localodoo_connection"),
            self._get_remote_connection(),
        ]:
            if not connection.is_local_connection:
                if os.getenv("DEVMODE") != "1":
                    continue
            self.env["zbs.test.order"].search([]).unlink()
            self.env["zbs.test.tag"].search([]).unlink()
            # force use of parent key to identify
            tag1 = self.env["zbs.test.tag"].create({"name": "tag1"})
            tag2 = self.env["zbs.test.tag"].create({"name": "tag2"})
            if not connection.is_local_connection:
                self.env.cr.commit()

            data = {
                "name": "order1",
                "___keys": ["name"],
                "tag_ids": [
                    {
                        "_type": "odoo_recordset",
                        "model": tag1._name,
                        "ids": tag1.ids,
                        "uid": self.env.uid,
                        "su": False,
                        "context": {},
                    },
                ],
            }
            if not connection.is_local_connection:
                # just test for error
                with self.assertRaises(ValidationError):
                    record, data = self._test_odoo_dumper(connection, data)
            else:
                record, data = self._test_odoo_dumper(connection, data)
                if connection.is_local_connection:
                    self.assertTrue(record)
                    self.assertEqual(record.name, "order1")
                    self.assertEqual(record.tag_ids.name, "tag1")
                    self.assertEqual(record.tag_ids.search_count([]), 2)
                    self.assertTrue(isinstance(data.created[0].id, int))
                else:
                    self.assertTrue(data.created)

                data = {
                    "name": "order1",
                    "___keys": ["name"],
                    "tag_ids": [
                        {
                            "_type": "odoo_recordset",
                            "model": tag1._name,
                            "ids": tag1.ids + tag2.ids,
                            "uid": self.env.uid,
                            "su": False,
                            "context": {},
                        }
                    ],
                }
                record, data = self._test_odoo_dumper(connection, data)
                if connection.is_local_connection:
                    self.assertTrue(record)
                    self.assertEqual(record.name, "order1")
                    self.assertIn("tag1", record.tag_ids.mapped("name"))
                    self.assertIn("tag2", record.tag_ids.mapped("name"))
                    self.assertEqual(record.tag_ids.search_count([]), 2)
                else:
                    self.assertTrue(data.updated)

                # test unlink (remove from record)
                data = {
                    "name": "order1",
                    "___keys": ["name"],
                    "___keys_delete": ["tag_ids"],
                    "tag_ids": [
                        {
                            "_type": "odoo_recordset",
                            "model": tag1._name,
                            "ids": tag1.ids,
                            "uid": self.env.uid,
                            "su": False,
                            "context": {},
                        },
                    ],
                }

                record, data = self._test_odoo_dumper(connection, data)
                if connection.is_local_connection:
                    self.assertTrue(record)
                    self.assertEqual(record.name, "order1")
                    self.assertIn("tag1", record.tag_ids.mapped("name"))
                    self.assertNotIn("tag2", record.tag_ids.mapped("name"))
                    self.assertEqual(record.tag_ids.search_count([]), 2)
                else:
                    self.assertTrue(data.updated)