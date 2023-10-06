from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class ZBSDumper(models.AbstractModel):
    _inherit = "zbs.worker"
    _name = "zbs.dumper"

    can_keys = fields.Boolean("Can Keys", compute="_compute_capas")
    can_keys_multi_ok = fields.Boolean("Multiple Keys allowed", compute="_compute_capas")
    can_delete_one2many = fields.Boolean("Can delete one2many", compute="_compute_capas")
    can_compare_delta = fields.Boolean("Can compare delta", compute="_compute_capas", help="Helpds for default values at write")

    def _compute_capas(self):
        for rec in self:
            rec.can_keys = False
            rec.can_keys_multi_ok = False
            rec.can_delete_one2many = False
            rec.can_compare_delta = False


class ZBSDumperMixinCU(models.AbstractModel):
    _name = "zbs.dumper.mixin.cu"

    do_insert = fields.Boolean("Do Insert", default=True)
    do_update = fields.Boolean("Do Update", default=True)