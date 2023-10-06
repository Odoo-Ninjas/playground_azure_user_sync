from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools.safe_eval import safe_eval


class MappingValues(models.Model):
    _name = "zbs.mapping.mapvalues"

    mapper_id = fields.Many2one("zbs.mapping", string="Mapper", xport_ignore=True)
    source_value = fields.Char("Source Value")
    dest_value = fields.Char("Dest Value")
    default_value = fields.Boolean("Default Value")
    strict_types = fields.Boolean(
        "Strict", help="if enabled, then a string is made like 'mystring'",
        related="mapper_id.strict_mapped_types", store=False
    )

    @api.constrains("default_value")
    def _changed_default_value(self):
        for rec in self:
            if rec.default_value:
                rec.mapper_id.mapped_value_ids.filtered(
                    lambda x: x.id != rec.id and rec.default_value
                ).write({"default_value": False})

    def _equals(self, X):
        self.ensure_one()
        value = self.as_value(self.source_value)
        return value == X

    def as_value(self, v):
        if self.strict_types:
            v = safe_eval(v)
        return v
