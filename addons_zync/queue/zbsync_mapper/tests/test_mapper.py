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
from odoo.addons.zbsync.tests.test_pipe import ZBSPipelineCase
from odoo.tests.common import Form
from ..models.mapping import FieldMissingException


class TestMapper(ZBSPipelineCase):
    def test_mappings_simple_direct(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = {
            "name": "testpartner1",
        }

        self.env["zbs.mapping"].create(
            {
                "step_id": mapper.id,
                "field_source": "name",
                "field_dest": "firstname",
                "action": "direct",
                "filter_to_delta": False,
            }
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(str(data._d), "[{'firstname': 'testpartner1'}]")

    def test_hierarchy(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = {
            "name": "testpartner1",
            "street": "strasse1",
        }

        self.env["zbs.mapping"].create(
            [
                {
                    "step_id": mapper.id,
                    "field_source": "name",
                    "field_dest": "firstname",
                    "action": "direct",
                    "filter_to_delta": False,
                },
                {
                    "step_id": mapper.id,
                    "field_source": "",
                    "field_dest": "address",
                    "action": "object",
                    "filter_to_delta": False,
                    "child_ids": [
                        (
                            0,
                            0,
                            {
                                "field_source": "street",
                                "field_dest": "street",
                                "filter_to_delta": False,
                            },
                        ),
                    ],
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            str(data._d),
            "[{'firstname': 'testpartner1', 'address': {'street': 'strasse1'}}]",
        )

    def test_hierarchy2(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = {
            "name": "testpartner1",
            "address": {
                "street": "strasse1",
            },
        }

        self.env["zbs.mapping"].create(
            [
                {
                    "step_id": mapper.id,
                    "field_source": "name",
                    "field_dest": "firstname",
                    "action": "direct",
                    "filter_to_delta": False,
                },
                {
                    "step_id": mapper.id,
                    "field_source": "address",
                    "field_dest": "address",
                    "action": "object",
                    "filter_to_delta": False,
                    "child_ids": [
                        (
                            0,
                            0,
                            {
                                "field_source": "street",
                                "field_dest": "street",
                                "filter_to_delta": False,
                            },
                        ),
                    ],
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            str(data._d),
            "[{'firstname': 'testpartner1', 'address': {'street': 'strasse1'}}]",
        )

    def test_hierarchy3(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = [[{"created": [[{"id": 313, "name": "partner313"}]]}]]

        self.env["zbs.mapping"].create(
            [
                {
                    "step_id": mapper.id,
                    "field_source": "created",
                    "field_dest": "",
                    "action": "object",
                    "filter_to_delta": False,
                    "child_ids": [
                        (
                            0,
                            0,
                            {
                                "field_source": "id",
                                "field_dest": "id",
                                "filter_to_delta": False,
                            },
                        ),
                    ],
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            str(data._d),
            "[{'id': 313}]",
        )

    def test_hierarchy4(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        mapper.no_metadata = True
        data = {"add1": {"street": "street1"}, "add2": {"street": "street2"}}

        self.env["zbs.mapping"].create(
            [
                {
                    "step_id": mapper.id,
                    "field_source": "add1",
                    "field_dest": "add1",
                    "action": "object",
                    "child_ids": [
                        (
                            0,
                            0,
                            {
                                "field_source": "street",
                                "field_dest": "street_mapped",
                            },
                        ),
                    ],
                },
                {
                    "step_id": mapper.id,
                    "field_source": "add2",
                    "field_dest": "add2",
                    "action": "object",
                    "child_ids": [
                        (
                            0,
                            0,
                            {
                                "field_source": "street",
                                "field_dest": "street_mapped",
                            },
                        ),
                    ],
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            data._d,
            [
                {
                    "add1": {"street_mapped": "street1"},
                    "add2": {"street_mapped": "street2"},
                }
            ],
        )

    def test_map_odooinstances(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        partner = self.env["res.partner"].create({"name": "otto waalkes"})

        self.env["zbs.mapping"].create(
            {
                "field_source": "name",
                "field_dest": "firstname",
                "action": "direct",
                "step_id": mapper.id,
            }
        )

        instance = pipe.start(partner)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            str(data._d),
            "[{'firstname': 'otto waalkes', '___filter_to_delta': True}]",
        )

    def test_mapped_values(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = {
            "name": "testpartner1",
            "color": "brown",
        }

        self.env["zbs.mapping"].create(
            {
                "step_id": mapper.id,
                "field_source": "color",
                "field_dest": "color_german",
                "action": "mapped_values",
                "filter_to_delta": False,
                "mapped_value_ids": [
                    (
                        0,
                        0,
                        {
                            "source_value": "brown",
                            "dest_value": "braun",
                        },
                    )
                ],
            },
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(str(data._d), "[{'color_german': 'braun'}]")

    def test_meta_values(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = {
            "name": "testpartner1",
        }

        self.env["zbs.mapping"].create(
            [
                {
                    "step_id": mapper.id,
                    "field_source": "name",
                    "field_dest": "firstname",
                    "action": "direct",
                    "is_key": True,
                    "filter_to_delta": False,
                },
                {
                    "step_id": mapper.id,
                    "field_source": "name",
                    "field_dest": "firstname",
                    "action": "direct",
                    "is_key": True,
                    "filter_to_delta": False,
                },
            ]
        )
        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            str(data._d), "[{'firstname': 'testpartner1', '___keys': ['firstname']}]"
        )

    def test_metadata_may_miss(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        initial_data = [
            {
                "name": "A",
            },
            {
                "name": "B",
                "name2": "C",
            },
        ]

        self.env["zbs.mapping"].create(
            [
                {
                    "step_id": mapper.id,
                    "field_source": "name",
                    "field_dest": "f1",
                    "action": "direct",
                    "filter_to_delta": False,
                },
                {
                    "step_id": mapper.id,
                    "field_source": "name2",
                    "field_dest": "f2",
                    "action": "direct",
                    "may_miss": True,
                    "filter_to_delta": False,
                },
            ],
        )

        instance = pipe.start(initial_data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(data._d, [{"f1": "A"}, {"f1": "B", "f2": "C"}])

        with self.assertRaises(FieldMissingException):
            mapper.root_mapping_ids()[1].may_miss = False
            instance = pipe.start(initial_data)
            instance.heartbeat()
            data = instance._eval_data()
            self.assertEqual(data._d, [{"f1": "A"}, {"f1": "B", "f2": "C"}])

    def test_unlink_subrecords(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        initial_data = [
            {"name": "A", "line_ids": [{"product": "A"}]},
        ]

        self.env["zbs.mapping"].create(
            [
                {
                    "step_id": mapper.id,
                    "field_source": "name",
                    "field_dest": "f1",
                    "action": "direct",
                    "filter_to_delta": False,
                },
                {
                    "step_id": mapper.id,
                    "field_source": "line_ids",
                    "field_dest": "lines",
                    "action": "direct",
                    "unlink_subrecords": True,
                    "filter_to_delta": False,
                },
            ],
        )

        instance = pipe.start(initial_data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            data._d,
            [{"f1": "A", "___keys_delete": ["lines"], "lines": [{"product": "A"}]}],
        )

    def test_default_value(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        initial_data = [
            {"name": "A", "line_ids": [{"product": "A"}]},
        ]

        self.env["zbs.mapping"].create(
            {
                "step_id": mapper.id,
                "field_source": "name",
                "field_dest": "f1",
                "action": "direct",
                "default_value": True,
            },
        )

        instance = pipe.start(initial_data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            data._d,
            [
                {
                    "f1": "A",
                    "___default_values": ["f1"],
                    "___filter_to_delta": True,
                }
            ],
        )

    def test_one2many(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = [
            {"name": "testpartner1", "field1": "A", "field2": "B"},
        ]

        self.env["zbs.mapping"].with_context(default_step_id=mapper.id).create(
            [
                {
                    "field_source": "name",
                    "field_dest": "name",
                    "action": "direct",
                    "filter_to_delta": False,
                },
                {
                    "field_source": "",
                    "field_dest": "contacts",
                    "action": "list",
                    "filter_to_delta": False,
                    "child_ids": [
                        (
                            0,
                            0,
                            {
                                "field_source": "",
                                "field_dest": "",
                                "action": "object",
                                "child_ids": [
                                    (
                                        0,
                                        0,
                                        {
                                            "field_source": "field1",
                                            "field_dest": "product",
                                            "action": "direct",
                                            "filter_to_delta": False,
                                        },
                                    )
                                ],
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "field_source": "",
                                "field_dest": "",
                                "action": "object",
                                "child_ids": [
                                    (
                                        0,
                                        0,
                                        {
                                            "field_source": "field2",
                                            "field_dest": "product",
                                            "action": "direct",
                                            "filter_to_delta": False,
                                        },
                                    )
                                ],
                            },
                        ),
                    ],
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            str(data._d),
            "[{'name': 'testpartner1', 'contacts': [{'product': 'A'}, {'product': 'B'}]}]",
        )

    def test_many2many_lookup(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = [
            {"name": "testpartner1", "countries": "Germany  ,  Switzerland"},
        ]

        self.env["zbs.mapping"].with_context(default_step_id=mapper.id).create(
            [
                {
                    "field_source": "name",
                    "field_dest": "name",
                    "action": "direct",
                    "filter_to_delta": False,
                },
                {
                    "field_source": "countries",
                    "field_dest": "marks",
                    "action": "lookup",
                    "filter_to_delta": False,
                    "lookup_model": "res.country",
                    "lookup_field": "name",
                    "format_value": (
                        "list(map(lambda x: x.strip(), value.split(',')))"
                    ),
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        country_germany = self.env.ref("base.de")
        country_switzerland = self.env.ref("base.ch")
        self.assertEqual(
            data._d,
            [
                {
                    "name": "testpartner1",
                    "marks": [country_germany.id, country_switzerland.id],
                }
            ],
        )

    def test_many2many_from_string(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = [
            {"name": "testpartner1", "countries": "Germany  ,  Switzerland"},
        ]

        self.env["zbs.mapping"].with_context(default_step_id=mapper.id).create(
            [
                {
                    "field_source": "name",
                    "field_dest": "name",
                    "action": "direct",
                    "filter_to_delta": False,
                },
                {
                    "field_source": "countries",
                    "field_dest": "marks",
                    "action": "list",
                    "filter_to_delta": False,
                    "format_value": (
                        "list(map(lambda x: x.strip(), value.split(',')))"
                    ),
                    "child_ids": [
                        (
                            0,
                            0,
                            {
                                "field_source": "countries",
                                "field_dest": "marks",
                                "action": "list",
                                "filter_to_delta": False,
                                "format_value": (
                                    "list(map(lambda x: x.strip(), value.split(',')))"
                                ),
                            },
                        )
                    ],
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        country_germany = self.env.ref("base.de")
        country_switzerland = self.env.ref("base.ch")
        self.assertEqual(
            data._d,
            [
                {
                    "name": "testpartner1",
                    "marks": [country_germany.id, country_switzerland.id],
                }
            ],
        )

    def test_many2many_from_string(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = [
            {"name": "testpartner1", "countries": "Germany  ,  Switzerland"},
        ]

        self.env["zbs.mapping"].with_context(default_step_id=mapper.id).create(
            [
                {
                    "field_source": "name",
                    "field_dest": "name",
                    "action": "direct",
                    "filter_to_delta": False,
                },
                {
                    "field_source": "countries",
                    "field_dest": "marks",
                    "action": "list",
                    "filter_to_delta": False,
                    "format_value": (
                        "list(map(lambda x: x.strip(), value.split(',')))"
                    ),
                    "child_ids": [
                        (
                            0,
                            0,
                            {
                                "field_source": "",
                                "field_dest": "",
                                "action": "object",
                                "filter_to_delta": False,
                                "child_ids": [
                                    (
                                        0,
                                        0,
                                        {
                                            "field_source": "$value",
                                            "field_dest": "name",
                                            "action": "direct",
                                            "filter_to_delta": False,
                                        },
                                    ),
                                    (
                                        0,
                                        0,
                                        {
                                            "field_source": "$value",
                                            "field_dest": "code",
                                            "action": "direct",
                                            "filter_to_delta": False,
                                            "format_value": ("value[:2].upper()"),
                                        },
                                    ),
                                ],
                            },
                        )
                    ],
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            data._d,
            [
                {
                    "name": "testpartner1",
                    "marks": [
                        {"code": "GE", "name": "Germany"},
                        {"code": "SW", "name": "Switzerland"},
                    ],
                }
            ],
        )

    def test_hierarchy_fieldsample(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = {
            "comment": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "besprechung"}],
                    }
                ],
            }
        }

        self.env["zbs.mapping"].create(
            [
                {
                    "step_id": mapper.id,
                    "action": "direct",
                    "filter_to_delta": False,
                    "field_source": "comment.content.content.text",
                    "field_dest": "text",
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            str(data._d),
            "[{'text': 'besprechung'}]",
        )

    def test_hierarchy_fieldsample2(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = {
            "comment": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "besprechung"}],
                    }
                ],
            }
        }

        self.env["zbs.mapping"].create(
            [
                {
                    "step_id": mapper.id,
                    "action": "direct",
                    "filter_to_delta": False,
                    "field_source": "comment.content[0].content[0].text",
                    "field_dest": "text",
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            str(data._d),
            "[{'text': 'besprechung'}]",
        )

    def test_many2one_lookup_specify_create_values(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        mapper.no_metadata = True
        data = [
            {"name": "testpartner1", "main_partner": "Germany"},
        ]

        self.env["zbs.mapping"].with_context(default_step_id=mapper.id).create(
            [
                {
                    "field_source": "main_partner",
                    "field_dest": "mainone",
                    "action": "lookup",
                    "filter_to_delta": False,
                    "lookup_model": "zbs.test.partner",
                    "lookup_field": "name",
                    "child_ids": [
                        [
                            0,
                            0,
                            {
                                "field_source": "'name1'",
                                "field_dest": "name",
                                "action": "eval",
                            },
                        ],
                        [
                            0,
                            0,
                            {
                                "field_source": "'DE'",
                                "field_dest": "country",
                                "action": "eval",
                            },
                        ],
                    ],
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._eval_data()
        self.assertEqual(
            data._d,
            [{"mainone": {"name": "name1", "country": "DE"}}],
        )

    def test_write_to_env(self):
        pipe, line = self.make_simple_pipe("zbs.mapper", {})
        mapper = line.worker_id
        data = [
            {
                "comment": "HALLO",
            }
        ]

        self.env["zbs.mapping"].create(
            [
                {
                    "step_id": mapper.id,
                    "action": "direct",
                    'output_stream': 'env',
                    "filter_to_delta": False,
                    "field_source": "comment",
                    "field_dest": "name1",
                },
            ]
        )

        instance = pipe.start(data)
        instance.heartbeat()
        data = instance._get_env()
        self.assertEqual(
            data["name1"],
            "HALLO",
        )