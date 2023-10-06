from odoo import _, api, fields, models, SUPERUSER_ID, tools
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from datetime import date, datetime
import odoorpc
from odoo.addons.zbsync.exceptions import ConfigurationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from copy import deepcopy
from contextlib import contextmanager


class WriteValues(dict):
    def __init__(self, *params, **kwparams):
        super().__init__(*params, **kwparams)
        self.odoo_id = None
        self.filter_delta = False
        self.default_values = []

    def set_odooid(self, id):
        self.odoo_id = id


class RemoveMe(object):
    def __init__(self, id):
        self.id = id


class OdooConnection(models.Model):
    _inherit = [
        "zbs.connection",
        "zbs.connection.mixin.usernamepassword",
        "zbs.connection.mixin.hostport",
    ]
    _name = "zbs.connection.odoo"

    timeout = fields.Integer("Timeout", default=120)

    port = fields.Integer(default=8069)
    dbname = fields.Char("DBName")
    is_local_connection = fields.Boolean(compute="_compute_is_local_connection")
    ssl = fields.Boolean("SSL")
    version = fields.Selection([(str(float(i)), str(float(i))) for i in range(99)])

    def _compute_is_local_connection(self):
        for rec in self:
            rec.is_local_connection = rec == self.env.ref(
                "zbsync_odoo.localodoo_connection"
            )

    def _get_field(self, model, fieldname):
        assert isinstance(model, str)
        res = self._get_fields_of_obj(model)
        res = [x for x in res if x["name"] == fieldname][0]
        return res

    def _get_obj(self, model):
        assert isinstance(model, str)
        if self.is_local_connection:
            obj = self.env[model]
            return obj
        else:
            rpc = self._get_odoo()
            return rpc.env[model]

    def _get_odoo(self):
        protocol = None
        if self.ssl:
            protocol = "jsonrpc+ssl"
        else:
            protocol = "jsonrpc"
        odoo = odoorpc.ODOO(
            self.host,
            port=self.port,
            protocol=protocol,
            version=float(self.version) or None,
            timeout=self.timeout,
        )
        dbname = self.dbname
        if not dbname:
            raise ConfigurationError("Please configure database name on connection.")
        odoo.login(dbname, self.username, self.password)
        return odoo

    @tools.cache("self.id", "model")
    def _get_fields_of_obj(self, model):
        obj = self._get_obj(model)
        _fields = self._odoo_search(
            obj.env["ir.model.fields"], [("model_id.model", "=", model)]
        )
        res = [
            {
                "comodel_name": x.relation,
                "name": x.name,
                "type": x.ttype,
                "inverse_name": x.relation_field,
            }
            for x in _fields
        ]
        res = self.env["zebrooset"].rs(res)
        return res

    def _odoo_search(self, obj, domain, *params, **kwparams):
        if self.is_local_connection:
            return obj.search(domain, *params, **kwparams)
        else:
            ids = obj.search(domain, *params, **kwparams)
            records = obj.browse(ids)
            return records

    @contextmanager
    def _filter_out(self, vals):
        store = {}
        for f in ["___kept_input"]:
            if f in vals:
                store[f] = vals.pop(f)
        try:
            yield vals
        finally:
            for k, v in store.items():
                vals[k] = v

    def _odoo_create(self, instance, obj, vals, lang):
        pipeline = self.env.context['pipeline']
        pipeline.log(f"Creating {obj._name}:\n{vals}")
        ids = []
        for val in vals:
            if self.is_local_connection:
                self = self.with_context(lang=lang or self.env.user.lang)
            with self._filter_out(val) as val2:
                id = obj.create(val2)
                if self.is_local_connection:
                    id = id.id
            val["id"] = id
            self._handle_create_write(obj, id, vals)
            ids.append(val)
        return ids

    def _odoo_write(self, instance, obj, vals, lang):
        pipeline = self.env.context['pipeline']
        pipeline.log(f"Updating {obj._name}:\n{vals}")
        ids = []
        for val in vals:
            assert isinstance(val, (WriteValues, RemoveMe))
            if self.is_local_connection:
                self = self.with_context(lang=lang or self.env.user.lang)
            if isinstance(val, RemoveMe):
                continue
            else:
                record = obj.browse(val.odoo_id)
                if val.default_values:
                    self._filter_default_values(val.default_values, record, val)
                if val.filter_delta:
                    val = self._filter_delta_values(record, val)

                if val:
                    with self._filter_out(val) as val2:
                        record.write(val2)
            ids.append((val.odoo_id, val))
            self._handle_create_write(record, val.odoo_id, val)
        return ids

    def _handle_create_write(self, model, odoo_id, vals):
        for field in ["create_date", "write_date"]:
            if isinstance(vals, dict):
                vals = [vals]
            for val in vals:
                if val.get(field):
                    if not self.is_local_connection:
                        raise ValidationError("Cannot update create_date / write_date remotely")
                    table = model._table
                    self.env.cr.execute(
                        f"update {table} set {field}=%s where id=%s",
                        (val[field], odoo_id),
                    )

    def _odoo_unlink(self, instance, obj, ids):
        pipeline = self.env.context['pipeline']
        pipeline.log(f"Deleting {obj._name}:\n{ids}")
        obj.browse(ids).unlink()
        return ids

    def _filter_default_values(self, fields, inst, data):
        for field in fields:
            if inst[field]:
                if field in data:
                    data.pop(field)

    def _filter_delta_values(self, inst, data):
        def _turn_into_datestring(v, format, maxlen):
            if not v:
                return v
            if isinstance(v, (date, datetime)):
                return v.strftime(format)
            result = v[:maxlen]
            if len(result) < maxlen:
                result += " 00:00:00"

        if not inst:
            return data
        all_fields = self._get_fields_of_obj(inst._name)
        for k in list(data.keys()):
            if k in ["___kept_input"]:
                continue
            f = [x for x in all_fields if x["name"] == k]
            if not f:
                raise KeyError(k)
            f = f[0]

            if f.type in ["integer", "float", "char", "text", "binary", "boolean"]:
                if f.type == "integer" and isinstance(data[k], str):
                    if data[k]:
                        data[k] = int(data[k])
                    else:
                        data[k] = 0
                elif f.type == "float" and isinstance(data[k], str):
                    if data[k]:
                        data[k] = float(data[k])
                    else:
                        data[k] = 0
                elif f.type == "char" and isinstance(data[k], (int, float)):
                    data[k] = str(data[k])
                elif f.type == "boolean" and isinstance(data[k], str):
                    if data[k] in ["1", "true", "True", "TRUE"]:
                        data[k] = True
                    elif data[k] in ["0", "false", "False", "FALSE"]:
                        data[k] = False
                    else:
                        raise NotImplementedError(data[k])
                v1 = data[k]
                v2 = inst[k]
                if v1 == v2:
                    del data[k]
            elif f.type in ["date"]:
                v1 = _turn_into_datestring(
                    (data[k] or "") or False, DEFAULT_SERVER_DATE_FORMAT, 10
                )
                v2 = _turn_into_datestring(
                    (inst[k] or "") or False, DEFAULT_SERVER_DATE_FORMAT, 10
                )
                if v1 == v2:
                    del data[k]
            elif f.type in ["datetime"]:
                v1 = _turn_into_datestring(
                    (data[k] or "") or False, DEFAULT_SERVER_DATETIME_FORMAT, 19
                )
                v2 = _turn_into_datestring(
                    (inst[k] or "") or False, DEFAULT_SERVER_DATETIME_FORMAT, 19
                )
                if v1 == v2:
                    del data[k]
            elif f.type == "many2one":
                v1 = data[k]
                v2 = inst[k].id
                if v1 == v2:
                    del data[k]
            elif f.type in ["one2many", "many2many"]:
                new_array = []
                if data[f.name]:
                    for x in data[f.name]:
                        if x and x[0] == 1:
                            sub_inst = inst[f.name].filtered(lambda x1: x1.id == x[1])
                            if sub_inst:
                                if tupled := isinstance(x, tuple):
                                    tupled = True
                                    x = list(x)
                                x[2] = self._filter_delta_values(sub_inst, x[2])
                                if tupled:
                                    x = tuple(x)
                                if not x[2]:
                                    continue
                        new_array.append(x)
                if not new_array:
                    data.pop(f.name)
                else:
                    data[f.name] = new_array
        return data

    def write(self, vals):
        res = super().write(vals)
        self.clear_caches()
        return res