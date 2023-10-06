from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.addons.zbsync.models.zebrooset import ZebrooSet
from odoo.tools.safe_eval import safe_eval


class FieldMissingException(Exception):
    pass


class Mapping(models.Model):
    _inherit = ["zbs.xport.mixin"]
    _name = "zbs.mapping"
    _order = "sequence"
    _parent_name = "parent_id"
    _parent_store = True

    current_mapper = fields.Many2one(
        "zbs.mapper", compute="_compute_mapper", search="_search_mapper"
    )
    no_metadata = fields.Boolean(related="current_mapper.no_metadata", store=False)

    name = fields.Char(compute="_compute_name", store=True)
    force_name = fields.Char("Force Name")
    active = fields.Boolean("Active", default=True)
    sequence = fields.Integer(default=9999)
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "zbs.mapping", "parent_id", string="Children", copy=True
    )
    may_miss = fields.Boolean("Source may miss")
    skip_if_empty = fields.Boolean("Skip if empty")
    unlink_subrecords = fields.Boolean("Unlink Subrecords")
    filter_to_delta = fields.Boolean("Filter Delta", default=True)
    no_create = fields.Boolean("No Create")
    no_update = fields.Boolean("No Update")
    default_value = fields.Boolean(
        "Default Value", help="Only set at write if False on other side"
    )
    # TODO implement
    filter_domain = fields.Char(
        "Filter Domain",
        help="e.g. record.name.startswith('a') or record.field in [1,2,3]",
    )
    # TODO quickformats
    pyfunc_id = fields.Many2one("zbs.mapping.pyfunc", string="Function")
    skip_record_expr = fields.Text("Expression to skip whole record")

    action = fields.Selection(
        [
            ("direct", "=>"),
            ("object", "{}"),
            ("list", "[]"),
            ("eval", "code"),
            ("mapped_values", "Value Mappings"),
            ("lookup", "Lookup"),  # TODO implement that record is created if not found
            # TODO trurnit lookup auf many2many auch machen z.B. wenn komma getrennt
            # environment values: they can be grabbed from data; is collected by file grabbers then
        ],
        string="Action",
        required=True,
        default="direct",
    )
    format_value = fields.Text("Format Expression", help="str(value).strip()")
    code = fields.Char("Code")
    field_source = fields.Char("Field Source")
    field_dest = fields.Char("Field Dest")
    parent_id = fields.Many2one(
        "zbs.mapping",
        string="Parent",
        index=True,
        ondelete="cascade",
        xport_ignore=True,
    )
    step_id = fields.Many2one("zbs.mapper", string="Step", xport_ignore=True)
    is_key = fields.Boolean("Is Key")
    level = fields.Integer("Level")
    hierarchy_indicator = fields.Char(
        "Hierarchy Indicator", compute="_compute_hierarchy_indicator", store=True
    )
    comment = fields.Text("Comment")
    mapped_value_ids = fields.One2many(
        "zbs.mapping.mapvalues", "mapper_id", string="Mapped Values"
    )
    strict_mapped_types = fields.Boolean("Strict Mapped Types")
    lookup_model = fields.Char("Lookup Model")
    lookup_field = fields.Char("Lookup Field")
    lookup_operator = fields.Selection(
        [("=", "="), ("ilike", "ilike"), ("like", "like")],
        string="Lookup Operator",
        default="ilike",
    )
    skip_if = fields.Selection(
        [
            ("never", "Never"),
            (
                "not_in_envs",
                "If not in env.fields",
            ),  # trigger method hook puts changed fields into 'fields'
        ]
    )
    output_stream = fields.Selection([("env", "Environment")])

    def open_mapping(self):
        return {
            "name": _("Mapping"),
            "view_type": "form",
            "res_model": self._name,
            "res_id": self.id,
            "context": {},
            "views": [(False, "form")],
            "type": "ir.actions.act_window",
            "target": "current",
        }

    def open_mapvalues(self):
        return {
            "name": _("Mapped Values"),
            "view_type": "form",
            "res_model": self.mapped_value_ids._name,
            "context": {
                "default_mapper_id": self.id,
            },
            "domain": [("mapper_id", "=", self.id)],
            "views": [(False, "tree")],
            "type": "ir.actions.act_window",
            "target": "current",
        }

    @api.constrains("parent_id")
    def _recalc_level_struct(self):
        roots = set()
        for rec in self:
            roots.add(rec.root)
        for root in roots:
            for el, level in root._traverse():
                el.level = level

    def _traverse(self, level=0):
        yield (self, level)
        for child in self.child_ids:
            yield from child._traverse(level + 1)

    @property
    def root(self):
        p = self
        while p.parent_id:
            p = p.parent_id
        return p

    def _compute_level(self):
        for rec in self:
            level = 0
            p = rec
            while p:
                p = p.parent_id
                level += 1
            rec.level = level - 1

    @api.depends("level")
    def _compute_hierarchy_indicator(self):
        for rec in self:
            rec._compute_level()
            if rec.level == 1:
                rec.hierarchy_indicator = "-"
            else:
                rec.hierarchy_indicator = "----" * (rec.level)

    @api.depends("field_dest", "field_source", "force_name")
    def _compute_name(self):
        for rec in self:
            if rec.force_name:
                rec.name = rec.force_name
            else:
                if not rec.field_source and not rec.field_dest:
                    rec.name = f"#{rec.id}"
                else:
                    rec.name = (
                        f"{rec.id}#{rec.field_source or ''} => {rec.field_dest or ''}"
                    )

    @api.model
    def _get_source_value(self, record, field):
        value = None
        try:
            # no dunder allowed mmphf

            def convert(x):
                if isinstance(x, str):
                    if "[" in x:
                        return x

                return f"['{x}']"

            if not field:
                raise ValidationError(f"Missing field for mapping #{self.id}")

            if "." in field:
                parts = "." + field
            else:
                parts = "".join(map(convert, field.split(".")))
            source_value = None
            if field:
                if "$value" not in field:
                    try:
                        source_value = record[field]
                    except Exception as ex:
                        source_value = record

            if "$value" in field:
                value = str(record)
            else:
                value = self.env["zbs.tools"].exec_get_result(
                    f"record{parts}", {"record": record, "value": source_value}
                )
        except (KeyError, ValueError) as ex:
            raise FieldMissingException(field) from ex
        except Exception as ex:
            raise Exception(f"Error at mapping: {self.id}") from ex
        else:
            if self.format_value:
                try:
                    value = self.env["zbs.tools"].exec_get_result(
                        self.format_value, {"value": value}
                    )
                except Exception as ex:
                    raise ValidationError(f"Error at mapping #{self.id}: {ex}") from ex
        return value

    def apply(self, record, mapped):
        from odoo.addons.zbsync.models import SkipRecord

        self.ensure_one()

        if self.skip_if == "not_in_envs" and self.field_source:
            instance_env = self.env.context.get("instance_env")
            try:
                env_fields = instance_env.fields
            except KeyError:
                pass
            else:
                if self.field_source not in env_fields:
                    return

        if self.skip_record_expr:
            value = self._get_source_value(record, self.field_source)
            if self.env["zbs.tools"].exec_get_result(
                self.skip_record_expr,
                {"record": record, "mapped": mapped, "value": value, "env": self.env},
            ):
                raise SkipRecord

        try:
            if self.action in ["direct"]:
                self._set_value(
                    mapped, self._get_source_value(record, self.field_source)
                )
            elif self.action in ["lookup"]:
                value = self._get_source_value(record, self.field_source)
                self._apply_lookup(value, mapped, record)

            elif self.action in ["object", "list"]:
                self._apply_object_list(record, mapped)
            elif self.action == "mapped_values":
                self._apply_mapped_values(record, mapped)
            elif self.action == "eval":
                self._apply_code(record, mapped)
            else:
                raise NotImplementedError(self.action)
        except FieldMissingException:
            if not self.may_miss:
                raise

        def default_list(name, value):
            if name not in mapped:
                mapped[name] = []
            if value not in mapped[name]:
                mapped[name].append(value)

        if isinstance(mapped, dict):
            if self.skip_if_empty and self.field_dest in mapped:
                # TODO Boolean vs. is NONE
                if not mapped[self.field_dest]:
                    mapped.pop(self.field_dest)

        if not self.no_metadata:
            if self.filter_to_delta and isinstance(mapped, dict):
                mapped["___filter_to_delta"] = True
            if self.no_create:
                mapped["___no_create"] = True
            if self.no_update:
                mapped["___no_update"] = True

            if self.is_key:
                default_list("___keys", self.field_dest)

            if self.default_value:
                default_list("___default_values", self.field_dest)

            if self.unlink_subrecords:
                default_list("___keys_delete", self.field_dest)

    def _write_to_env(self, env_expression, value):
        inst = self.env.context["instance"]
        env = inst._get_env()
        env_expression = f"env.{env_expression} = value\nTrue"
        self.env["zbs.tools"].exec_get_result(
            env_expression,
            {"env": env, "value": value},
        )
        inst._set_env(env)

    def _set_value(self, mapped, value, dest_field=None):
        dest_field = dest_field or self.field_dest
        if self.output_stream == "env":
            self._write_to_env(dest_field, value)
        else:
            mapped[self.field_dest] = value

    def _apply_2env(self, value):
        instance = self.env.context.get("instance")
        env = instance._get_env()
        env[self.field_dest] = value
        instance._set_env(env)

    def _apply_lookup(self, value, mapped, record):
        dest_field, model, field = self.field_dest, self.lookup_model, self.lookup_field
        if not model or not field:
            raise ValidationError("Please provide lookup-model and field!")
        if not value:
            self._set_value(mapped, False, dest_field)

        is_list = isinstance(value, (list, tuple))
        if not is_list:
            value = [value]
        res = []
        for _v in value:
            if not _v:
                res.append(None)
                continue
            matches = self.env[model].search([(field, self.lookup_operator, _v)])
            if len(matches) > 1:
                raise ValidationError(
                    f"Mapping #{self.id}: Too many values found in {model} for {_v}"
                )
            if len(matches) == 1:
                res.append(matches[0].id)
            elif not matches:
                if not self.child_ids:
                    # create item in dumper
                    if not self.no_metadata:
                        res.append({field: _v, "___keys": [field]})
                else:
                    self._apply_object_list(record, mapped, action="object")
                    res.append(mapped[self.field_dest])

        if not is_list:
            res = res[0]
        self._set_value(mapped, res, dest_field=dest_field)

    def _apply_code(self, record, mapped):
        from odoo.addons.zbsync.models import SkipRecord
        code = self.code or self.field_source
        value = None
        if self.field_source:
            try:
                value = self._get_source_value(record, self.field_source)
            except Exception:
                value = self.field_source  # seems to contain code
        try:
            res = self.env["zbs.tools"].exec_get_result(
                code,
                {"record": record, "mapped": mapped, "value": value, "env": self.env},
            )
        except SkipRecord:
            raise
        except Exception as ex:
            raise Exception(
                f"Error for evaluating {self.field_source}=>{self.field_dest}:\n{ex}"
            ) from ex
        if isinstance(mapped, list):
            mapped.append(res)
        else:
            self._set_value(mapped, res)

    def _apply_object_list(self, record, mapped, action=None):
        from odoo.addons.zbsync.models import SkipRecord

        object = None
        action = action or self.action
        if action == "object":
            if isinstance(mapped, list):
                mapped.append({})
                object = mapped[-1]
            else:
                if not self.field_dest:
                    object = mapped
                else:
                    self._set_value(mapped, {})
                    object = mapped[self.field_dest]
        elif action == "list":
            self._set_value(mapped, [])
            object = mapped[self.field_dest]

        if self.child_ids:
            for child in self.child_ids:
                subset = record
                if self.field_source:
                    if self.action != "lookup":
                        subset = self._get_source_value(subset, self.field_source)
                if isinstance(subset, (list, models.Model)) and isinstance(
                    object, list
                ):
                    for item in subset:
                        try:
                            child.apply(item, object)
                        except SkipRecord:
                            continue
                else:
                    try:
                        child.apply(subset, object)
                    except SkipRecord:
                        continue
        return mapped

    def _apply_mapped_values(self, record, mapped):
        source_value = self._get_source_value(record, self.field_source)
        if not source_value and self.skip_if_empty:
            return
        mapval = self.mapped_value_ids.filtered(lambda x: x._equals(source_value))
        if not mapval and not source_value:
            mapval = self.mapped_value_ids.filtered(lambda x: x.default_value)

        if not mapval:
            raise ValidationError(
                f"Value {source_value} not found in mapping {self.name} (#{self.id})"
            )
        if len(mapval) > 1:
            raise ValidationError(
                f"Value {source_value} found multiple times in "
                f"mapping {','.join(filter(bool, mapval.mapped('dest_value')))}"
            )
        self._set_value(mapped, mapval.as_value(mapval.dest_value))

    # TODO copy should copy the children, too

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        return res

    @api.model
    def create(self, vals):
        if not vals.get("step_id"):
            if vals.get("parent_id"):
                parent = self.browse(vals["parent_id"])
                vals["step_id"] = parent.step_id.id
        res = super().create(vals)
        return res

    def ok(self):
        return True

    @api.depends_context("pipeline")
    def _compute_mapper(self):
        for rec in self:
            pl = self.env.context.get("pipeline")
            if not pl:
                rec.current_mapper = False
                continue
            rec.current_mapper = pl.worker_id

    def _search_mapper(self, operator, value):
        if isinstance(value, list):
            assert all(isinstance(x, int) for x in value)
        res = self.env["zbs.mapper"].search([("id", operator, value)])
        return [("id", "in", res.ids)]
