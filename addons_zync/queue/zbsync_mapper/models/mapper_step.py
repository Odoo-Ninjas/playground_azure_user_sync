from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.addons.zbsync.models.zebrooset import ZebrooSet


class ZBSMapperStep(models.Model):
    _inherit = "zbs.worker"
    _name = "zbs.mapper"

    can_keys = fields.Boolean("Can Keys", tracking=True)
    mapping_ids = fields.One2many(
        "zbs.mapping", "step_id", string="Mappings", tracking=True
    )
    no_metadata = fields.Boolean("No Metadata", tracking=True, default=False)

    def _compute_can_open_worker_detail(self):
        for rec in self:
            rec.can_open_worker_detail = True

    def root_mapping_ids(self):
        self.ensure_one()
        return self.mapping_ids.filtered(lambda x: not x.parent_id)

    def process_record(self, instance, index, record, data):
        mapped = {}
        for mapping in self.root_mapping_ids():
            mapping.apply(record, mapped)
        return mapped

    def _apply_keep_input_merge_record(self, rec, kept):
        rec['___kept_input'] = kept

    def open_action(self):
        self.ensure_one()
        return {
            "name": _("Mapping"),
            "view_type": "form",
            "view_mode": "form",
            "context": {
                "default_step_id": self.id,
                "active_test": False,
            },
            "res_model": "zbs.mapping",
            "domain": [("step_id", "=", self.id)],
            "views": [(False, "list")],
            "type": "ir.actions.act_window",
            "target": "current",
        }

    def _compute_can_open_worker_detail(self):
        for rec in self:
            rec.can_open_worker_detail = True

    def open(self):
        return {
            "view_type": "form",
            "res_model": self._name,
            "res_id": self.id,
            "views": [(False, "form")],
            "type": "ir.actions.act_window",
            "target": "current",
        }
