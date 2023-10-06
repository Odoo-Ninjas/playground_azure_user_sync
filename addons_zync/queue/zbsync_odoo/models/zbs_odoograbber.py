from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import odoorpc
import logging

logger = logging.getLogger("zbsync.grabber.odoo")


class Domain(models.Model):
    _inherit = ["zbs.domain", "zbs.xport.mixin"]
    _name = "zbs.domain.odoo"

    parent_id = fields.Many2one("zbs.grabber.odoo")


class OdooGrabber(models.Model):
    _inherit = ["zbs.grabber", "zbs.odoo.mixin.connection", "zbs.domains.mixin"]
    _name = "zbs.grabber.odoo"

    domain_ids = fields.One2many("zbs.domain.odoo", tracking=True)
    fields_to_read = fields.Char("Fields (comma separated)", tracking=True)
    is_local_connection = fields.Boolean(related="connection_id.is_local_connection")
    odoo_as = fields.Selection(
        [
            ("json", "JSON"),
            ("browse", "Browsable Object"),
        ],
        string="Format-Type",
        default="json",
        tracking=True,
        required=True,
    )

    def _slugme(self, instances, _fields):
        for inst in instances:
            for k in _fields:
                inst[k] = self._slug(inst[k])
            del inst
        return instances

    def _get_fields(self):
        self.ensure_one()
        if self.fields_to_read:
            return self.fields_to_read.split(",")
        all_fields = self.connection_id._get_fields_of_obj(self.model)
        return [x["name"] for x in all_fields]

    def process(self, instance, data):
        result_instances = None
        self.connection_id.clear_caches()

        for index, record in self._iterate_data(data):
            domain = self.resolve_domain(instance, data=record, record=record) or []

            obj = self.connection_id._get_obj(self.model)
            instances = self.connection_id._odoo_search(obj, domain)

            if self.odoo_as == "json":
                _fields = self._get_fields()
                instances = self._slugme(instances.read(_fields) or [], _fields)
                self._apply_keep_input(index, record, data, instances)
                if result_instances is None:
                    result_instances = []
                result_instances += instances

            elif self.connection_id.is_local_connection:
                if result_instances is None:
                    result_instances = self.env[self.model]
                result_instances |= instances

            elif self.odoo_as == "browse":
                if result_instances is None:
                    result_instances = instances
                else:
                    result_instances |= instances
            else:
                raise NotImplementedError(self.odoo_as)
            del instances
            del obj

        return instance.Result(result_instances)

    @api.model
    def _slug(self, v):
        if isinstance(v, odoorpc.models.BaseModel):
            return v.id
        if isinstance(v, int):
            return v
        if not v:
            return False
        if isinstance(v, (tuple, list)) and len(v) > 1:
            return v[0]
        return v
