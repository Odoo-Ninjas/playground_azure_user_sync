# TODO Marc: some code smells here; indented functions
"""

fields:


from odoo import _, api, fields, models, SUPERUSER_ID
fields.XXXX(xport_ignore=True)  - to leave out field
fields.XXXX(xport_rule='by_name')  - at many2one: to lookup many2one record by name in source and destination
fields.XXXX(xport_rule='custom', xport_export='function string name', xport_import='function string name')

    @api.model
    def export_data(self, value):
        return {
        }

    @api.model
    def import_data(self, value):
        self.search ....
        return field_value to set

"""
from odoo import tools
import threading
import json
import uuid
from datetime import datetime, date
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError

MAX_RETRIES_ON_MISSING = 1000


def str2instance(env, x):
    if not x:
        return False
    splitted = x.split(",")
    return env[splitted[0]].browse(int(splitted[1]))


class Skip(Exception):
    pass


class NotFoundByName(Exception):
    def __init__(self, model, name):
        self.model = model
        self.name = name
        super().__init__(f"Not found: {model} {name}")


class Base(models.AbstractModel):
    _inherit = "base"

    def _valid_field_parameter(self, field, name):
        return name == "xport_ignore" or super()._valid_field_parameter(field, name)


class ImportExportMixing(models.AbstractModel):
    _name = "zbs.xport.mixin"

    zync_uuid = fields.Char(
        "XPort UUID", default=lambda x: str(uuid.uuid4()), copy=False, required=True
    )
    _sql_constraints = [
        (
            "zync_uuid_unique",
            "unique(zync_uuid)",
            _("Only one unique entry allowed."),
        ),
    ]

    def dump(self, parent=None):
        already_exported = set()
        result = parent or {}
        result.update(self._get_fields_as_pydata(already_exported))
        return result

    def _get_fields_as_pydata(self, already_exported):
        if not self:
            return False
        self.ensure_one()
        record_key = f"{self._name},{self.id}"
        if self in already_exported:
            return ("use_existing", record_key)
        data = {}
        already_exported.add(self)
        for field_name, field in sorted(
            self._fields.items(), key=lambda k: k[0], reverse=False
        ):
            if field_name in [
                "create_date",
                "create_uid",
                "write_uid",
                "write_date",
                "__last_update",
                "id",
            ]:
                continue
            if field_name in [
                x for x in self.env["mail.thread"]._fields if x not in ["id"]
            ]:
                continue
            if getattr(field, "xport_ignore", False):
                continue
            if getattr(field, "related", False):
                continue

            value = self[field_name]
            if field.type != "boolean" and value is False:
                continue
            try:
                val = self._xport_convert_for_export(
                    data, value, field, already_exported
                )
                if val is None:
                    val = False
                data[field_name] = val
            except Skip:
                continue
            # if 'many' in field.type:
        data["__record_id"] = record_key
        return data

    def _xport_many2one_ref_by_name(self, value):
        if not value:
            return False
        name = value.name_get()[0][1]
        return (
            "by_name",
            {
                "name": name,
                "model": value._name,
                "id": value.id,
            },
        )

    def _xport_get_id_of_object(self, obj):
        if not obj:
            return False
        data = self.env["ir.model.data"]._get_upmost_id(obj._name, obj.id)
        if not data:
            return

        return ("xmlid", data[0].module + "." + data[0].name)

    def _xport_many2one_ref_by_get_fields_as_pydata(
        self, data, value, f, already_exported
    ):
        data = value._get_fields_as_pydata(already_exported)
        if f.type == "reference":
            if data:
                if isinstance(data, tuple):
                    # is internal datatype like ('use_existing', )
                    pass
                else:
                    data["___model"] = value._name
        return data

    def _xport_many2one_reference(self, data, value, f, already_exported):
        rule = getattr(f, "xport_rule", None)
        if rule == "by_name":
            return self._xport_many2one_ref_by_name(value)

        # xmlid must win over get fields; one item can be by xmlid,
        # but the others are created on the fly
        xmlid = self.env["ir.model.data"]._get_upmost_id(value._name, value.id)
        if not xmlid:
            if hasattr(value, "_get_fields_as_pydata"):
                return self._xport_many2one_ref_by_get_fields_as_pydata(
                    data, value, f, already_exported
                )

        return self._xport_get_id_of_object(value)

    def _xport_x2many(self, value, f, already_exported):
        _l = []
        for data in value.sorted(lambda x: x.id):
            try:
                if hasattr(data, "_get_fields_as_pydata"):
                    data = data._get_fields_as_pydata(already_exported)
                else:
                    data = self._xport_get_id_of_object(data)
                _l.append(data)
            except Skip:
                continue
        return _l

    def _xport_pack(self, data, value, f, already_exported):
        if getattr(f, "xport_rule", False) == "custom":
            return ("custom", getattr(self, f.xport_export)(value))

        if f.type in ("many2one", "reference"):
            return self._xport_many2one_reference(data, value, f, already_exported)

        if f.type in ["many2many", "one2many"]:
            return self._xport_x2many(value, f, already_exported)

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")

        return value

    @api.model
    def _xport_convert_for_export(self, data, value, f, already_exported):
        if not f.store or f.compute:
            return False

        value = self._xport_pack(data, value, f, already_exported)

        if isinstance(value, bytes):
            # TODO - check encoding; or serialize bytewise
            value = value.decode("utf-8")
        return value

    @api.model
    def _import_resolve_by_name(self, name, model, id):
        recs = self.env[model].search([]).filtered(lambda x: x.name_get()[0][1] == name)
        if not recs:
            raise NotFoundByName(model, name)
        if len(recs) > 1:
            raise Exception(f"Too many records found for: {name}")
        return recs

    @api.model
    def load(self, data, override_values=None):
        mapping_create_id_with_given_ids = {}
        self = self.with_context(zync_import=True)

        existing = None
        if data.get('zync_uuid'):
            existing = self.search([('zync_uuid', '=', data['zync_uuid'])], limit=1, order='id desc')

        data = self._import_convert_dict(
            data, self, None, mapping_create_id_with_given_ids
        )
        if existing:
            data['id'] = existing.id

        for k, v in (override_values or {}).items():
            data[k] = v

        if not data.get("id", False):
            flow = self.create(data)
        else:
            flow = self.browse(data["id"])
            flow.write(data)
        return flow

    def _import_interprete_complex_import_rule(
        self, d, field, mapping_create_id_with_given_ids
    ):
        instance = None
        if isinstance(d, (tuple, list)) and len(d) == 2:
            if d[0] == "xmlid":
                instance = self.env.ref(d[1])

            elif d[0] == "use_existing":
                if d[1] not in mapping_create_id_with_given_ids:
                    raise KeyError(f"Not found: {d[1]}")
                instance = mapping_create_id_with_given_ids[d[1]]

            elif d[0] == "by_name":
                key = f"{d[1]['model']},{d[1]['id']}"
                if key in mapping_create_id_with_given_ids:
                    instance = mapping_create_id_with_given_ids[key]
                else:
                    instance = self._import_resolve_by_name(**d[1])
            elif d[0] == "custom":
                instance = getattr(self.env[field.model_name], field.xport_import)(d[1])
            else:
                raise NotImplementedError(d[0])

        return instance

    def _import_x2many_field(
        self, create_data, d, k, field, mapping_create_id_with_given_ids
    ):
        arr = []
        if not d[k]:
            create_data[k] = arr
            return

        for x in d[k]:
            sub_obj = self.env[field.comodel_name]
            # problem at 0, 0 is, that for "use_existing" no ids are made
            # arr.append((0, 0, _convert_dict(x, sub_obj, field)))
            data = self._import_convert_dict(
                x, sub_obj, field, mapping_create_id_with_given_ids
            )
            if data is None:
                continue
            if isinstance(data, int):
                id = data
            elif isinstance(data, models.BaseModel):
                id = data.id
            else:
                existing = False
                if data.get("zync_uuid"):
                    existing = sub_obj.search([("zync_uuid", "=", data["zync_uuid"])])
                if existing:
                    id = existing[0].id
                    existing[0].write(data)

                else:
                    id = sub_obj.create(data).id
                del existing

            if isinstance(x, dict):  # could be ['use_existing', 'model,id']
                mapping_create_id_with_given_ids[x["__record_id"]] = sub_obj.browse(id)
            arr.append((4, id))
        create_data[k] = arr

    def _import_convert_dict_record_by_zync_uuid(
        self, data, sub_obj, d, k, field, mapping_create_id_with_given_ids
    ):
        existing = sub_obj.search([("zync_uuid", "=", data["zync_uuid"])])
        if existing:
            existing.write(data)
            id = existing[0].id
        else:
            id = sub_obj.create(data).id
        if (
            data.get("__record_id", False)
            and data["__record_id"] in mapping_create_id_with_given_ids
        ):
            raise Exception(f"Duplicate Record creation: {d['__record_id']}\n {d}")
        instance = sub_obj.browse(id)
        mapping_create_id_with_given_ids[d[k]["__record_id"]] = instance
        return instance

    def _import_convert_many2one_reference(
        self, create_data, d, k, field, mapping_create_id_with_given_ids
    ):
        v = d[k]
        sub_obj = None
        if field.type == "reference":
            if isinstance(d[k], dict):
                sub_obj = self.env[d[k].pop("___model")]

        else:
            sub_obj = self.env[field.comodel_name]

        id = False
        if v:
            data = self._import_convert_dict(
                d[k], sub_obj, field, mapping_create_id_with_given_ids
            )
            if isinstance(data, dict):
                instance = self._import_convert_dict_record_by_zync_uuid(
                    data, sub_obj, d, k, field, mapping_create_id_with_given_ids
                )
                if instance:
                    sub_obj = self.env[instance._name]
                    id = instance.id
            elif isinstance(data, int):
                id = data
            elif isinstance(data, models.BaseModel):
                sub_obj = self.env[data._name]
                id = data.id

        if id:
            create_data[k] = self._import_convert_fieldtype(
                field, f"{sub_obj._name},{id}"
            )
        elif id is not None:
            create_data[k] = id

    def _import_convert_fieldtype(self, field, value):
        if field.type == "reference":
            if isinstance(value, models.BaseModel):
                return f"{value._name},{value.id}"
            elif isinstance(value, str):
                return value
            else:
                return value
        elif field.type == "many2one":
            if isinstance(value, models.BaseModel):
                return value.id
            elif isinstance(value, str):
                id = int(value.split(",")[1])
                return id
            else:
                return value
        else:
            return value

    def _import_convert_dict(self, d, obj, field, mapping_create_id_with_given_ids):
        instance = self._import_interprete_complex_import_rule(
            d, field, mapping_create_id_with_given_ids
        )
        if instance is not None:
            return instance

        if not d:
            return None
        if d["__record_id"] in mapping_create_id_with_given_ids:
            instance = mapping_create_id_with_given_ids[d["__record_id"]]
            return instance

        assert isinstance(d, dict)
        create_data = {}

        # can be that other fields import and create for example backend models
        retried = {}
        todo = sorted(list(d.keys()))

        while todo or retried:
            if todo:
                k = todo.pop(0)
            else:
                k = sorted(list(retried.keys()))[0]
            try:
                if k not in obj._fields:
                    if not k.startswith("_"):
                        raise Exception(f"Field not found: {k}")
                    continue
                field = obj._fields[k]

                if field.type in ["one2many", "many2many"]:
                    self._import_x2many_field(
                        create_data, d, k, field, mapping_create_id_with_given_ids
                    )
                elif field.type in ["many2one", "reference"]:
                    self._import_convert_many2one_reference(
                        create_data, d, k, field, mapping_create_id_with_given_ids
                    )
                else:
                    create_data[k] = d[k]

            except NotFoundByName as ex:
                print(str(ex))
                if retried.get(k, 0) > MAX_RETRIES_ON_MISSING:
                    raise
                retried.setdefault(k, 0)
                retried[k] += 1
            else:
                if k in retried:
                    del retried[k]

        return create_data
