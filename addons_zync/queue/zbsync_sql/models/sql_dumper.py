"""
Expects key columns in [{'___keys': ....}]
"""
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.addons.zbsync.models.zebrooset import ZebrooSet
from .expression import WhereExpression
from datetime import date, datetime
import logging
logger = logging.getLogger()

class SqlDumper(models.Model):
    _inherit = [
        "zbs.dumper",
        "zbs.sql.connection.mixin",
        "zbs.dumper.mixin.cu",
    ]
    _name = "zbs.plain.sql"

    plain_sql = fields.Text("Plain SQL")
    execute_per_record = fields.Boolean("Execute per Record", help="If true, then there is a record variable otherwise only input exists.")
    fetch = fields.Selection([
        ('fetchall', 'Fetch All'),
        ('fetchnone', 'No Fetch'),
    ])

    def _compute_capas(self):
        for rec in self:
            rec.can_keys = False
            rec.can_keys_multi_ok = False
            rec.can_delete_one2many = False
            rec.can_compare_delta = False

    def process(self, instance, data):
        self = self.with_context(instance=instance)
        if not self.fetch:
            raise ValidationError("Please define fetching")

        def store_kept(res, kept):
            if self.fetch == 'fetchnone':
                res = kept
            else:
                res = {
                    'data': res,
                    'kept': kept,
                }
            return res

        result = []
        zs_data = self.env["zebrooset"].rs(data) if isinstance(data, (dict, list)) else input
        with self.connection_id._get_conn() as cr:
            with self.connection_id._in_transaction(cr, "plain-sql-#{self.id}") as cr:
                if self.fetch == 'fetchnone':
                    method = self.connection_id.execute 
                elif self.fetch == 'fetchall':
                    method = self.connection_id.fetchall

                params = {
                    'data': zs_data,
                    'input': zs_data,
                }

                if self.execute_per_record:
                    for i, record in enumerate(data._iterate_records()):
                        params['record'] = record
                        sql = self.env['zbs.tools'].exec_get_result(self.plain_sql, params)
                        # ACTIVATE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # res = method(cr, sql, tuple([]))
                        kept = self._keep_input(i, record, zs_data)

                        res = store_kept(record, kept)
                        result.append(res)

                else:
                    method(cr, self.plain_sql, params)
                    sql = self.env['zbs.tools'].exec_get_result(self.plain_sql, params)
                    res = getattr(self.connection_id, method)(cr, sql, tuple([]))
                    kept = self._keep_input(0, zs_data, zs_data)
                    res = store_kept(data, kept)
                    result.append(res)

        return instance.Result(result)

class SqlDumper(models.Model):
    _inherit = [
        "zbs.dumper",
        "zbs.sql.connection.mixin",
        "zbs.dumper.mixin.cu",
    ]
    _name = "zbs.dumper.sql"
    _description = "Stores data in sql databases"

    table = fields.Char("Table", required=False)
    recreate_record = fields.Boolean("Recreate record", help="If record exists (by key values) it gets deleted before being update")

    def _compute_capas(self):
        for rec in self:
            rec.can_keys = True
            rec.can_keys_multi_ok = True
            rec.can_delete_one2many = False
            rec.can_compare_delta = False

    def process(self, instance, data):
        self = self.with_context(instance=instance)

        creates, updates = [], []
        result = {"create": [], "update": []}

        with self.connection_id._get_conn() as cr:
            with self.connection_id._in_transaction(cr, self.table) as cr:
                for i, record in enumerate(data._iterate_records()):
                    logger.info(f"sql iterate records {i} done")
                    keys = self._get_keys(record)
                    keep = self._keep_input(i, record, data)
                    existing_record = None
                    if keys:
                        existing_record = self._find_record(cr, record)
                    if existing_record and self.recreate_record:
                        self._delete_record(cr, record)
                    if existing_record:
                        if self.do_update:
                            updates.append((existing_record, record, keep))
                    else:
                        if self.do_insert:
                            creates.append(record, keep)

                def _store_kept(record, keep):
                    record = self.env['zebrooset'].rs(record)
                    record._merge(keep)
                    return record

                for i, (keys, record, keep) in enumerate(updates):
                    if not i % 10:
                        logger.info(f"sql update records {i} done")
                    self._update_record(cr, keys, record)
                    record = _store_kept(record, keep)
                    result["update"].append(record)

                logger.info("Creating records")
                self._create_record(cr, creates)
                for record, keep in creates:
                    record = _store_kept(record, keep)
                result["create"] = [x[0] for x in creates]

        return instance.Result(result)

    def _build_domain(self, keys, record):
        domain = []
        if not keys:
            return domain
        for key in keys:
            domain.append((key, "=", record[key]))
        return domain

    def _get_keys(self, record):
        keys = record._d.get("___keys")
        if not keys:
            return None
        return keys

    def _delete_record(self, cr, record):
        keys = self._get_keys(record)
        if not keys:
            raise ValidationError("No keys defined - cannot delete a record")
        domain = self._build_domain(keys, record)
        whereclause, whereparams = WhereExpression(
            domain, self.connection_id.type
        ).get_clause()
        plain_where = whereclause or " 1=1 "
        sql = f"DELETE FROM {self.table_sql} WHERE {plain_where}"
        self.connection_id.execute(cr, sql, whereparams)

    def _find_record(self, cr, record):
        keys = self._get_keys(record)
        if not keys:
            return None

        domain = self._build_domain(keys, record)
        whereclause, whereparams = WhereExpression(
            domain, self.connection_id.type
        ).get_clause()
        sql = self._build_sql(self._get_fields(keys), whereclause)
        recs = self.connection_id.fetchall(cr, sql, whereparams)
        return recs and recs[0] or None

    @property
    def table_sql(self):
        table = self.table
        if "(" not in table:
            table = WhereExpression._escape(table)
        return table

    def _build_sql(self, fields, where_clause):
        sql = ["select"]

        sql_fields = self._get_fields(fields)
        sql += [",".join(sql_fields)]
        sql += [f"from {self.table_sql}"]
        plain_where = where_clause or " 1=1 "
        sql += [f"where {plain_where}"]

        # if order_by:
        #     sql += ["order by {}".format(order_by)]
        sql = "\n".join(sql)
        return sql

    def _get_fields(self, fields):
        sql_fields = []
        if not fields:
            sql_fields = ["*"]
        else:
            for f in fields:
                if not f:
                    raise Exception("Field may not be null.")
                f = WhereExpression._escape(f)
                sql_fields.append(f)
        return sql_fields

    def _filter_fields(self, keys):
        return [x for x in keys if x not in ["___keys"]]

    def _create_record(self, cr, records):
        if not records:
            return
        record1 = records[0]
        fields = list(self._filter_fields(record1.keys()))
        escaped_fields = [WhereExpression._escape(x) for x in fields]

        sql = ["insert into "]
        sql += [self.table_sql]

        sql += ["("]
        sql += [",".join(escaped_fields)]
        sql += [")"]

        # if dialect == 'mssql':
        # sql += [" output"]
        # inserted = []
        # for idfield in model._get_id_fields_in_order():
        # inserted.append("Inserted.{}".format(WhereExpression._escape(idfield)))
        # sql += [",".join(inserted)]

        values = []
        sql += [" values"]

        for record in records:
            val = []
            for field in fields:
                fieldval = record[field]
                if isinstance(fieldval, list):
                    if len(fieldval) < 1:
                        fieldval = ""
                    elif len(fieldval) == 1:
                        fieldval = fieldval[0]
                    else:
                        fieldval = [",".join("{}" for x in fieldval)]
                val.append(fieldval)  # [record[x] for x in fields]
            values.append(tuple(val))

        placeholder = self.connection_id.placeholder
        sql_values = ["(" + ",".join(placeholder for x in fields) + ")"]

        sql = "".join(sql) + ",".join(sql_values)
        try:
            cr.executemany(sql, values)
        except Exception as ex:
            raise Exception(f"SQL Used: {sql} with params: {values}") from ex

    def _update_record(self, cr, keys, record):
        fields = list(self._filter_fields(record.keys()))
        update_values = []

        sql = ["update"]
        sql += [self.table_sql]
        sql += ["set"]
        placeholder = self.connection_id.placeholder

        update_params = []
        for field in fields:
            update_values.append(record[field])
            update_params.append(f"{WhereExpression._escape(field)} = {placeholder}")
        sql += [",".join(update_params)]

        sql += ["where"]
        id_fields = record["___keys"]
        where_sql = []
        for i, id_field in enumerate(id_fields):
            where_sql.append(f"{id_field} = {placeholder}")
            update_values.append(keys[id_field])
        sql += [",".join(where_sql)]
        sql = "\n".join(sql)
        update_values = tuple(update_values)
        try:
            cr.execute(sql, update_values)
        except Exception as ex:
            raise Exception(f"SQL Used: {sql} with params: {update_values}") from ex

    @api.model
    def convert_value_to_sql(value):
        if isinstance(value, (int, float, bool)):
            value = str(value)
        elif value is None:
            value = "null"
        elif isinstance(value, str):
            if "\n" in value:
                raise ValidationError(f"Not allowed: linebreak in {value}")
            value = "'" + value.replace("'", "''") + "'"
        elif isinstance(value, datetime):
            value = value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, date):
            value = value.strftime("%Y-%m-%d")
        return value
