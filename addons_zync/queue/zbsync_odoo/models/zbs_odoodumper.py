"""
Expects key columns in [{'___keys': ....}]
"""
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DT
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.addons.zbsync.models.zebrooset import ZebrooSet
from .zbs_odooconnection import WriteValues, RemoveMe
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
from contextlib import contextmanager

# TODO cache fields
# TODO locking if main key exists or so
# TODO raise retryable job error then
# TODO domain mapping values
"""

{
    "name": "name1",
    "___keys": ["name"],
    "___keys_multi_ok": True/False,
    "___keys_delete": ["line_ids"], list of fields, where to delete missing keys
    "___filter_to_delta": True/False
    "___default_values: ['field1', 'field2']
    "line_ids": [
        {.....},
        {.....},
        {.....},
    ],
}


"""

ALL_META_ATTRS = [
    "___keys",
    "___keys_multi_ok",
    "___keys_delete",
    "___filter_to_delta",
    "___default_values",
    "___kept_input",
]


class OdooDumper(models.Model):
    _inherit = ["zbs.dumper", "zbs.dumper.mixin.cu", "zbs.odoo.mixin.connection"]
    _name = "zbs.dumper.odoo"

    only_new_values = fields.Boolean("Only New Values", tracking=True)
    lang = fields.Char("Language", default="en_US", tracking=True)

    def process(self, instance, data):
        pipeline = self.env.context['pipeline']
        self = self.with_context(instance=instance)
        self.connection_id.clear_caches()
        content = data._d
        if isinstance(content, dict):
            content = [content]
        if not self.model:
            raise ValidationError("Please provide a model!")

        obj = self.connection_id._get_obj(self.model)
        create_vals, write_vals = self._get_create_write_values(
            obj, content, root=True, input=data
        )
        data = {"created": [], "updated": []}
        for create_val in create_vals:
            data["created"] += (
                self.connection_id._odoo_create(
                    instance, obj, [create_val], lang=self.lang
                )
            )
        pipeline.log(f"Creating for {obj._name}:\n{create_vals}")
        data["updated"] = self.connection_id._odoo_write(
            instance, obj, write_vals, lang=self.lang
        )
        return instance.Result([data])

    def _get_create_write_values(
        self,
        obj,
        records,
        parent_id=None,
        inverse_field=None,
        delete_x2many=False,
        parent_field=None,
        parent_obj=None,
        root=False,
        input=None,
    ):
        create_vals, write_vals = [], []
        add_domain = []
        ids = []
        for (
            record,
            id,
            kept_input,
        ) in self._iterate_for_values(
            records, obj, ids, inverse_field, parent_id, root, input
        ):
            no_update = record.get("___no_update") if hasattr(record, 'get') else False
            no_create = record.get("___no_create") if hasattr(record, 'get') else False
            if not id and no_create:
                continue
            if id and no_update:
                continue
            (
                values,
                _filter_to_delta,
                _default_values,
            ) = self._transform_input_to_values(record, id, obj, parent_obj)
            del record

            if root:
                values["___kept_input"] = kept_input
            if not id:
                create_vals.append(values)
            else:
                values = WriteValues(values)
                values.set_odooid(id)
                values.default_values = _default_values
                values.filter_delta = _filter_to_delta
                write_vals.append(values)

        if parent_id and delete_x2many:
            self._execute_kill_command_delete_x2many(
                obj,
                add_domain,
                ids,
                parent_field,
                parent_id,
                parent_obj,
                write_vals,
            )

        return create_vals, write_vals

    @api.model
    def _sort_fields(self, record, obj_fields):
        def sortit(fieldname):
            if fieldname in ALL_META_ATTRS:
                return -1
            field = [x for x in obj_fields if x.name == fieldname]
            if not field:
                if fieldname.startswith("___"):
                    return 0
                raise KeyError(fieldname)
            field = field[0]
            # higher prio, so that "id" is evaluated first
            if field.type in ["one2many", "many2many"]:
                return 100
            if field.type in ["many2one"]:
                return 10
            return 0

        sorteddict = {}
        for fieldname in record:
            sorteddict[fieldname] = sortit(fieldname)
        for fieldname, value in sorted(record.items(), key=lambda x: sorteddict[x[0]]):
            yield fieldname, value

    @api.model
    def _get_obj_field(self, fieldname, obj, obj_fields):
        field = None
        if fieldname not in ALL_META_ATTRS:
            if not fieldname.startswith("___") and fieldname not in [
                x["name"] for x in obj_fields
            ]:
                raise KeyError(f"{fieldname} not in {obj._name}")

            field = [x for x in obj_fields if x.name == fieldname]
            if field:
                field = field[0]
        return field

    def _slice_dictionary(
        self,
        record,
        id,
        obj,
        obj_fields,
        values,
        parent_obj,
        _filter_to_delta,
        _default_values,
    ):
        for fieldname, value in self._sort_fields(record, obj_fields):
            field = self._get_obj_field(fieldname, obj, obj_fields)

            if field and field.type == "many2one":
                if fieldname in record:
                    values[fieldname] = self._import_many2one(
                        obj, fieldname, record[fieldname]
                    )
            elif field and field.type in ["one2many", "many2many"]:
                values[fieldname] = self._import_x2many(
                    obj,
                    fieldname,
                    record[fieldname],
                    parent_id=id or record.get("id"),
                    parent_obj=parent_obj,
                    inverse_field=field.inverse_name,
                    delete_keys=fieldname in record.get("___keys_delete", []),
                )

            elif fieldname == "___filter_to_delta":
                _filter_to_delta = True
            elif fieldname == "___default_values":
                _default_values = value

            elif fieldname in ALL_META_ATTRS:
                continue
            elif fieldname.startswith("___"):
                continue
            else:
                if isinstance(value, datetime):
                    value = value.strftime(DTF)
                if isinstance(value, date):
                    value = value.strftime(DT)
                values[fieldname] = value
        return _filter_to_delta, _default_values, values

    def _iterate_for_values(
        self, records, obj, ids, inverse_field, parent_id, root, input
    ):
        add_domain = []
        if inverse_field and parent_id:
            add_domain = [(inverse_field, "=", parent_id)]
        for index, record in enumerate(records):
            kept_input = None
            if isinstance(record, (dict, list)):
                record = self.env["zebrooset"].rs(record)
            if root:
                kept_input = self._keep_input(
                    index,
                    record,
                    self.env["zebrooset"].rs(input)
                    if isinstance(input, (dict, list))
                    else input,
                )
            if inverse_field and not parent_id:  # one2many:
                id = None
            else:
                id = self._find_id(
                    obj,
                    record,
                    add_domain=add_domain,
                )
            ids.append(id)

            if root:
                if not id and not self.do_insert:
                    continue
                if id and not self.do_update:
                    continue

            yield record, id, kept_input

    def _transform_input_to_values(
        self,
        record,
        id,
        obj,
        parent_obj,
    ):
        _filter_to_delta = False
        _default_values = []
        values = {}
        obj_fields = self.connection_id._get_fields_of_obj(obj._name)
        if isinstance(record, (str, float, datetime, date)):
            if self.connection_id.is_local_connection:
                record = {obj._rec_name: record}
            else:
                # TODO fits in 99,9% of cases, but not always
                record = {"name": record}

        if isinstance(record, int):
            record = {"id": record}
        if isinstance(record, models.Model):
            if self.connection_id.is_local_connection:
                record = record
            else:
                raise ValidationError(
                    f"Cannot dump to remote odoo system some odoo instances like {record}.\n"
                    "There are no key informations given. Please map those records to "
                    "[]/{} combination(s) and set appropriate keys.\n\n"
                    "A thorough explanation can be found here: TODO"
                )
        if type(record).__name__ == "_WrappedList" or isinstance(record, list):
            if type(record).__name__ == "_WrappedList":
                record = record._l
            values = record
        elif isinstance(record, models.Model):
            if self.connection_id.is_local_connection:
                values = [6, 0, record.ids]
            else:
                raise ValidationError(
                    f"Cannot dump to remote odoo system some odoo instances like {record}.\n"
                    "There are no key informations given. Please map those records to "
                    "[]/{} combination(s) and set appropriate keys.\n\n"
                    "A thorough explanation can be found here: TODO"
                )
        else:
            _filter_to_delta, _default_values, values = self._slice_dictionary(
                record,
                id,
                obj,
                obj_fields,
                values,
                parent_obj,
                _filter_to_delta,
                _default_values,
            )
        return values, _filter_to_delta, _default_values

    def _execute_kill_command_delete_x2many(
        self, obj, add_domain, ids, parent_field, parent_id, parent_obj, write_vals
    ):
        kill_command = self._delete_x2many_comparing_keys(
            obj,
            add_domain,
            list(filter(bool, ids)),
            parent_field=parent_field,
            parent_id=parent_id,
            parent_obj=parent_obj,
        )
        for kill in kill_command:
            kill.parent_id = parent_id
            kill.parent_field_name = parent_field["name"]
            kill.parent_obj = parent_obj._name
            write_vals.append(kill)

    def _delete_x2many_comparing_keys(
        self,
        obj,
        add_domain,
        keep_ids,
        parent_field,
        parent_id=None,
        parent_obj=None,
    ):
        ttype = parent_field.type
        if ttype == "one2many":
            existing = self.connection_id._odoo_search(obj, add_domain)
            kill = [
                x.id for x in existing if x.id not in keep_ids
            ]  # compatible with remote odoorpc
            self.connection_id._odoo_unlink(self.env.context["instance"], obj, kill)
            return []
        elif ttype == "many2many":
            if parent_id:
                parent_field_name = parent_field["name"]
                existing = parent_obj.browse(parent_id)[parent_field_name]
                return [
                    RemoveMe(x.id) for x in existing if x.id not in keep_ids
                ]  # compatible with remote odoorpc
            else:
                return []
        else:
            raise NotImplementedError()

    def _import_many2one(self, obj, fieldname, values):
        if not values:
            return False
        comodel_name = self.connection_id._get_field(obj._name, fieldname)[
            "comodel_name"
        ]
        if isinstance(values, int):
            return values
        elif isinstance(values, bool) and not values:
            return False

        if self.connection_id.is_local_connection:
            key_values, domain = self._xtract_keyvalues(values)
            if key_values:
                self.env["zbs.tools"].pg_advisory_lock_keyvalues(obj._name, key_values)

        obj = self.connection_id._get_obj(comodel_name)
        create_vals, write_vals = self._get_create_write_values(obj, [values])
        assert len(create_vals) + len(write_vals) <= 1
        if create_vals:
            ids = self.connection_id._odoo_create(
                self.env.context["instance"], obj, create_vals, lang=self.lang
            )
            return ids[0]["id"]
        elif write_vals:
            ids = self.connection_id._odoo_write(
                self.env.context["instance"], obj, write_vals, lang=self.lang
            )
            return ids[0][1].odoo_id
        else:
            raise NotImplementedError(values)

    def _import_x2many(
        self,
        obj,
        fieldname,
        values,
        parent_id=None,
        parent_obj=None,
        inverse_field=None,
        delete_keys=None,
    ):
        if not values:
            return None
        field = self.connection_id._get_field(obj._name, fieldname)
        comodel_name = field["comodel_name"]
        parent_obj = obj
        obj = self.connection_id._get_obj(comodel_name)
        create_vals, write_vals = self._get_create_write_values(
            obj,
            values,
            parent_id=parent_id,
            inverse_field=inverse_field,
            delete_x2many=delete_keys,
            parent_field=field,
            parent_obj=parent_obj,
        )
        res = []
        for w in write_vals:
            if inverse_field:
                res.append((1, w.odoo_id, w))
            else:
                self.connection_id._odoo_write(
                    self.env.context["instance"], obj, write_vals, lang=self.lang
                )
                if isinstance(w, RemoveMe):
                    res.append((3, w.id))
                else:
                    res.append((4, w.odoo_id))
        for c in create_vals:
            if type(c).__name__ == "_WrappedList" or isinstance(c, list):
                if type(c).__name__ == "_WrappedList":
                    c = c._l
                res += [c]
            elif isinstance(c, models.Model):
                res += [[4, x.id] for x in c]
            else:
                res.append((0, 0, c))

        return res

    def _xtract_keyvalues(self, values):
        if "___keys" not in values:
            return None, None
        keys = values["___keys"]
        keyvalues = {}
        domain = []
        for key in keys:
            domain.append((key, "=", values[key]))
            keyvalues[key] = values[key]
        return keyvalues, domain

    def _find_id(self, obj, values, add_domain=[]):
        if isinstance(values, int):
            return values
        if isinstance(values, str):
            res = obj.name_search(values, operator="=")
            if res:
                return res[0][0]
            return None

        if not isinstance(values, dict) and values.__class__.__name__ not in [
            "ZebrooSet",
            "_WrappedDict",
        ]:
            return None
        if "id" in values and values["id"]:
            return values["id"]

        if "___keys" in values:
            keyvalues, domain = self._xtract_keyvalues(values)

            if add_domain:
                domain = expression.AND([domain, add_domain])

            if self.connection_id.is_local_connection:
                self.env["zbs.tools"].pg_advisory_lock_keyvalues(obj._name, keyvalues)
            records = self.connection_id._odoo_search(obj, domain, order="id desc")
            if len(records) > 1:
                if values.get("___keys_multi_ok"):
                    records = records[0]
                else:
                    raise ZebrooSet.TooManyrecordsException(
                        f"Too many records found for: {domain} - "
                        "you can set keys multi ok to change this behaviour."
                    )
            if not records:
                return None
            return records[0].id

    def _compute_capas(self):
        for rec in self:
            rec.can_keys = True
            rec.can_keys_multi_ok = True
            rec.can_delete_one2many = True
            rec.can_compare_delta = True
