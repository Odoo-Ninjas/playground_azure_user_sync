from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ZbsDomains(models.AbstractModel):
    _name = "zbs.domains.mixin"

    domain_ids = fields.One2many("zbs.domain", "parent_id", string="Domains")

    def resolve_domain(self, instance, data, record=None):
        usage = "normal"
        if instance.test_mode:
            usage = "test"
        domain = self.domain_ids.filtered(lambda x: x.usage == usage)
        if not domain:
            if self.domain_ids:
                domain = self.domain_ids.sorted()[0]
            else:
                domain = ""
        if isinstance(domain, models.AbstractModel):
            domain = domain.eval(data, record=record)
        return domain


class Domain(models.AbstractModel):
    _inherit = ["mail.thread"]
    _name = "zbs.domain"
    _order = "sequence"

    name = fields.Char("Name", default="-", tracking=True)
    sequence = fields.Integer("Sequence", default=9999)
    parent_id = fields.Many2one(xport_ignore=True)
    usage = fields.Selection(
        [("test", "Test"), ("normal", "Normal")],
        required=True,
        default="normal",
        tracking=True,
    )
    domain = fields.Text(
        "Domain", required=True, tracking=True, help="SQL or Odoo Domain or whatever"
    )

    def eval(self, data, record=None):
        self.ensure_one()
        instance = self.env.context.get("instance")
        objects = instance._get_default_objects({"data": data, "record": record})
        domain = "res = (\n" + (self.domain or "[]") + "\n)\nres"
        domain = self.env["zbs.tools"].exec_get_result(domain, objects)
        return domain
