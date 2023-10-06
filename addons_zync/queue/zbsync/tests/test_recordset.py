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
from odoo.addons.zbsync.models.zebrooset import ZebrooSet
from copy import deepcopy


class TestRecordset(TransactionCase):
    """

    rec:
      - [
            ('name', 'myname', )
            ('children', rec, 'list')
                          |
                          |- [

                          ]
        ]



    """

    def test_odoo_models(self):
        user = self.env.user
        dumped = ZebrooSet._dumps(user, self.env)
        rs2 = ZebrooSet._loads(dumped, env=self.env)
        self.assertEqual(rs2, user)
        rs2 = self.env["zebrooset"].loads(dumped)
        self.assertEqual(rs2, user)

    def test_recordset(self):
        rs = ZebrooSet(
            {
                "name": "Hans",
                "more": {"nachname": "Wimmer"},
                "created": [13],
            }
        )
        self.assertEqual(rs.more.__parent__.name, "Hans")
        self.assertEqual(rs.created[0], 13)
        rs = ZebrooSet(
            {
                "name": "Hans",
                "more": {"nachname": "Wimmer"},
                "more1": {
                    "more2": {
                        "more3": {
                            "name": "Haspel",
                        }
                    },
                },
            }
        )
        self.assertEqual(rs.more.__parent__.name, "Hans")
        self.assertEqual(rs.more1.more2.__parent__.__parent__.name, "Hans")
        self.assertEqual(
            rs.more1.more2.more3.__parent__.__parent__.__parent__.name, "Hans"
        )
        self.assertEqual(rs.more1.more2.more3.__root__.name, "Hans")
        rs = ZebrooSet(
            {
                "name": "Hans",
                "more": [[[{"nachname": "Wimmer"}]]],
            }
        )
        self.assertEqual(rs.name, "Hans")
        self.assertEqual(rs.nAme, "Hans")
        self.assertEqual(rs.more.nachname, "Wimmer")
        self.assertEqual(rs.more.nAchname, "Wimmer")

        rs = ZebrooSet(
            {
                "name": "Hans",
                "more": [
                    {"nachname": "Wimmer"},
                    {"nachname1": "Wimmer1"},
                    {"nachname2": "Wimmer2"},
                ],
            }
        )
        self.assertEqual(rs.name, "Hans")
        self.assertEqual(rs.nAme, "Hans")
        with self.assertRaises(ZebrooSet.TooManyrecordsException):
            self.assertEqual(rs.more.nachname, "Wimmer")
        self.assertEqual(rs.more[1].nachname1, "Wimmer1")

        rslist = ZebrooSet([])
        self.assertEqual(len(rslist), 0)
        rslist2 = ZebrooSet([[]])
        self.assertEqual(len(rslist2), 1)
        rsdict = ZebrooSet({})
        self.assertEqual(len(rsdict), 0)
        rs = ZebrooSet([{"name": "hans"}])

        data = {
            "name": "hansi",
            "data": "data1",
            "children": [
                {"childname1": "child1"},
            ],
        }
        rs = ZebrooSet(data)
        self.assertEqual(rs.name, "hansi")
        self.assertEqual(rs.data, "data1")
        self.assertEqual(rs.children.childname1, "child1")

        data = [
            {
                "name": "hansi",
                "data": "data1",
                "children": [
                    {"childname1": "child1"},
                ],
            }
        ]
        rs = ZebrooSet(data)
        self.assertEqual(rs.name, "hansi")
        self.assertEqual(rs.data, "data1")
        self.assertEqual(rs.children.childname1, "child1")

        data = [
            [
                {
                    "name": "hansi",
                    "data": "data1",
                    "children": [
                        {"childname1": "child1"},
                    ],
                }
            ]
        ]
        rs = ZebrooSet(data)
        self.assertEqual(rs.name, "hansi")
        self.assertEqual(rs.data, "data1")
        self.assertEqual(rs.children.childname1, "child1")

        data = ZebrooSet(
            {
                "lines": [
                    {"product": "prod1"},
                    {"product": "prod2"},
                ]
            }
        )
        checked = []
        for rec in data.lines:
            checked.append(rec.product)
        self.assertIn("prod1", checked)
        self.assertIn("prod2", checked)

        data = ZebrooSet(
            {
                "orders": [
                    {
                        "lines": [
                            {"product": "prod1"},
                            {"product": "prod2"},
                        ]
                    }
                ]
            }
        )
        checked = []
        for rec in data.orders.lines:
            checked.append(rec.product)
        self.assertIn("prod1", checked)
        self.assertIn("prod2", checked)

    def test_iterations(self):
        rs = ZebrooSet(
            [
                {"name": "A"},
                {"name": "B"},
            ]
        )

        met = []
        for record in rs._iterate_records():
            met.append(record.name)

        self.assertIn("A", met)
        self.assertIn("B", met)

    def test_exceptions(self):
        rs = ZebrooSet({"name": "A"})

        with self.assertRaises(KeyError):
            rs.name2

    def test_set_values(self):
        rs = ZebrooSet({"name": "A"})
        rs.name = "B"
        self.assertEqual(rs.name, "B")

        rs = ZebrooSet({"name": "A", "sub": {"name": "A"}})
        rs.sub.name = "B"
        self.assertEqual(rs.sub.name, "B")

        rs = ZebrooSet({"name": "A", "sub": {"name": "A"}})
        rs.newfield = "maria"
        self.assertEqual(rs.newfield, "maria")
        rs.newobject = {}
        rs.newobject.name = "max"
        self.assertEqual(rs.newobject.name, "max")
        rs.newlist = []
        rs.newlist.append({})
        rs.newlist.name = "agatha"
        self.assertEqual(rs.newlist.name, "agatha")

        rs.newlist2 = []
        rs.newlist2 += ["a"]

        t = ZebrooSet({})
        t.a = "asd"

    def test_duplicate_keys(self):
        rs = ZebrooSet({"name": "A"})
        with self.assertRaises(ValueError):
            rs.Name = "B"

    def test_apply_doubleasterisk(self):
        def method(**params):
            self.assertEqual(params["name"], "A")
            self.assertNotIn("___metainfo", params)

        rs = ZebrooSet({"name": "A"})
        method(**rs)
        rs = ZebrooSet({"name": "A", "sub": {"name": "A"}})
        method(**rs.sub)
        rs = ZebrooSet({"name": "A", "___metainfo": 1})
        method(**rs)

    def test_apply_params(self):
        def method(*params):
            self.assertEqual(params[0], "A")

        rs = ZebrooSet(["A"])
        method(*rs)
        rs = ZebrooSet({"sub": ["A"]})
        method(*rs.sub)

    def test_arrays(self):
        test = ZebrooSet([1])
        self.assertEqual(test[0], 1)
        test = ZebrooSet([{"a": "b"}])
        self.assertEqual(test[0].a, "b")

    def test_reserved_words(self):
        with self.assertRaises(Exception):
            test = ZebrooSet({"a": "b"})
            test.keys = "not allowed"
            test.items = "not allowed"

    def test_strange_names(self):
        test = ZebrooSet({})
        test["name-bc!"] = "a"
        self.assertEqual(test["name-bc!"], "a")
        test["a"] = {}
        test.a["b-c"] = {
            "value": "asd",
        }
        self.assertEqual(test.a["b-c"].__parent__["b-c"].value, "asd")
        self.assertEqual(test.a["b-c"]["__parent__"]["b-c"].value, "asd")

    def test_with_tuples(self):
        test = ZebrooSet({"a": (1, 2, 3)})
        self.assertEqual(test.a[0], 1)

    def test_merge(self):
        test = ZebrooSet({"a": "b"})
        test2 = ZebrooSet({"c": "d"})
        test._merge(test2)
        self.assertEqual(test._d, {"a": "b", "c": "d"})

        test = ZebrooSet({"A": {"a": "b"}})
        test2 = ZebrooSet({"A": {"c": "d"}})
        test._merge(test2)
        self.assertEqual(test._d, {"A": {"a": "b", "c": "d"}})

        test = ZebrooSet([{"A": {"a": "b"}}])
        test2 = ZebrooSet([{"A": {"c": "d"}}])
        test._merge(test2)
        self.assertEqual(test._d, [{"A": {"a": "b", "c": "d"}}])

        test = ZebrooSet([{"A": [{"a": "b"}]}])
        test2 = ZebrooSet([{"A": [{"c": "d"}]}])
        test._merge(test2)
        self.assertEqual(test._d, [{"A": [{"a": "b", "c": "d"}]}])

        test = ZebrooSet({"A": {"a": "1"}})
        test2 = ZebrooSet({"A": {"b": "2"}})
        test.A._merge(test2)
        self.assertEqual(test._d, {"A": {"a": "1", "A": {"b": "2"}}})

        test = ZebrooSet({"A": {"a": "1"}})
        test2 = ZebrooSet({"A": {"b": "2"}})
        test.A._merge(test2.A)
        self.assertEqual(test._d, {"A": {"a": "1", "b": "2"}})

        test = ZebrooSet([{"A": {"a": "1"}}])
        test2 = ZebrooSet([{"A": {"b": "2"}}])
        test.A._merge(test2.A)
        self.assertEqual(test._d, [{"A": {"a": "1", "b": "2"}}])

        test = ZebrooSet([{"A": [{"a": "1"}]}])
        test2 = ZebrooSet([{"A": [{"b": "2"}]}])
        test.A._merge(test2.A)
        self.assertEqual(test._d, [{"A": [{"a": "1", "b": "2"}]}])

        test = ZebrooSet({})
        test2 = ZebrooSet({"f": 1})
        test._merge(test2)
        self.assertEqual(test.f, 1)

    def test_metainfo(self):
        test = ZebrooSet({"name": "Anton"})
        test["___AA"] = 3

        self.assertEqual(test["___AA"], 3)

        # TODO assign to list
        # test = ZebrooSet({"name": ["Anton"]})
        # test.name["___AA"] = 4
        # self.assertEqual(test.name["___AA"], 4)

        # test._meta({"keys": ["a", "b"]})
        # self.assertEqual(test["___keys"], ["a", "b"])

    def test_metainfo_serialization(self):
        test = ZebrooSet({"name": ["Anton"]})
        test["___keys"] = ["a", "b"]
        dumpresult = test._dumps(test, self.env)
        test2 = ZebrooSet._loads(dumpresult, env=self.env)
        self.assertEqual(test2["___keys"]._l, ["a", "b"])

    def test_metainfo_serialization_dict(self):
        test = ZebrooSet({"A": {"B": "C"}})
        test.A["___m1"] = "m2"
        dumpresult = test._dumps(test, self.env)
        test2 = ZebrooSet._loads(dumpresult, env=self.env)
        self.assertEqual(test2.A["___m1"], "m2")

    def test_get(self):
        test = ZebrooSet({"A": {"B": "C"}})
        a = test.get("A")
        b = test.A.get("B")
        self.assertEqual(a, {"B": "C"})
        self.assertEqual(b, "C")

        self.assertTrue("A" in test)
        self.assertTrue("B" in test.A)

    def test_isinstance(self):
        test = ZebrooSet({"A": {"B": "C"}})
        self.assertEqual(test.__class__.__name__, "ZebrooSet")

    def test_assign_string_deepdive_list(self):
        rs = ZebrooSet([[{"a": "1"}]])
        rs["b"] = "2"
        self.assertEqual(rs[0][0].b, "2")

    def test_hierarch(self):
        data = [[{"created": [[{"id": 313, "name": "partner313"}]]}]]
        data = ZebrooSet(data)
        for rec in data._iterate_records():
            self.assertEqual(rec["created"].id, 313)

    def test_item(self):
        data = [{"name": "heinz"}]
        data = ZebrooSet(data)
        self.assertEqual(json.dumps(data[0]._d), json.dumps({"name": "heinz"}))

    def test_json(self):
        orig = [{"name": "heinz"}]
        data = ZebrooSet(orig)
        self.assertEqual(data._as_json(), orig)
        self.assertEqual(data[0]._as_json(), orig[0])

    def test_joining(self):
        r1 = [{"name": "1"}]
        t1 = ZebrooSet(deepcopy(r1)) + []
        t2 = ZebrooSet([deepcopy(r1[0])]) + []
        t3 = ZebrooSet(deepcopy(r1)) + [{}]
        t4 = ZebrooSet([deepcopy(r1[0])]) + [{}]
        self.assertTrue([x for x in t1._iterate_records() if x.get("name") == "1"])
        self.assertTrue([x for x in t1._iterate_records() if x.get("name") == "1"])
        self.assertEqual(len(t1), 1)
        self.assertEqual(len(t2), 1)
        self.assertEqual(len(t3), 2)
        self.assertEqual(len(t4), 2)

    def test_slice(self):
        r1 = ZebrooSet([1, 2, 3])
        t1 = r1[:1]
        self.assertEqual(t1[0], 1)

        r1 = ZebrooSet([{"field": "value"}, {"field1": "value1"}])
        t1 = r1[1:]
        self.assertEqual(t1[0]["field1"], "value1")

        r1 = ZebrooSet([{"field": [1, 2, 3]}])
        t1 = r1["field"][1:2]
        self.assertEqual(t1._l, [2])

    def test_extraction(self):
        r1 = ZebrooSet([[{"field": "value"}, {"field2": "value2"}]])
        test = r1[0]

        for rec in r1[0]._iterate_records():
            pass

    def test_setdefault(self):
        d = {'a': 1}
        d = ZebrooSet(d)
        d.setdefault('b', {'d': 2})
        d.b.setdefault('e', 3)

    def test_wraplist(self):
        d = {'a': 1}
        d = ZebrooSet(d)
        d._wraplist()
        assert isinstance(d._d, list)
        assert d._d == [{'a': 1}]