from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class PipelineTag(models.Model):
    _name = "zbs.pipeline.tag"

    name = fields.Char("Name", required=True)
