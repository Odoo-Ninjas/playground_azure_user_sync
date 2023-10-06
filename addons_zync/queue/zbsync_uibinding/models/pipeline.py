from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError

# TODO add list action in 16.0


class Pipeline(models.Model):
    _inherit = "zbs.pipeline"

    form_action_model_id = fields.Many2one("ir.model", string="Add Form Action here", xport_ignore=True)
    parent_menu_id = fields.Many2one("ir.ui.menu", string="Parent Menu", xport_ignore=True)
    created_window_action_ids = fields.One2many("ir.actions.act_window", "pipeline_id", xport_ignore=True)
    created_menu_item_ids = fields.One2many("ir.ui.menu", "pipeline_id", xport_ignore=True)

    def _check_uibinding_model(self):
        model = self.form_action_model_id.model
        if not model:
            raise UserError(_("No model found."))
        return model

    def add_form_action(self):
        model = self._check_uibinding_model()
        button_caption = self.name
        pipeline_id = self.id
        if not model:
            raise UserError(_("No model found."))
        xml = (
            "<header position='inside'>"
            "<button name='start_action_zbsync_from_button' "
            f"type='object' "
            f"string='{button_caption}' "
            f"context=\"{{'pipeline_id': {pipeline_id}, 'active_id': context.get('active_id'), 'active_model': context.get('active_model')}}\" "
            ">"
            "</button>"
            "</header>"
        )
        main_views = (
            self.env["ir.ui.view"]
            .sudo()
            .search(
                [
                    ("type", "=", "form"),
                    ("mode", "=", "primary"),
                    ("model", "=", model),
                    ("inherit_id", "=", False),
                    ("arch_db", "ilike", "<header"),
                ]
            )
        )

        for main_view in main_views:
            form_name = f"pipeline-buttonaction-{model}-{pipeline_id}-{main_view.id}"
            views = (
                self.env["ir.ui.view"]
                .sudo()
                .search(
                    [
                        ("type", "=", "form"),
                        ("name", "=", form_name),
                    ]
                )
            )

            if not views:
                views = views.sudo().create(
                    {
                        "name": form_name,
                        "type": "form",
                        "arch_db": xml,
                        "model": model,
                    }
                )
            views.sudo().write({"arch_db": xml, "inherit_id": main_view.id})

    def remove_form_action(self):
        model = self._check_uibinding_model()
        self.env["ir.ui.view"].sudo().search(
            [
                ("name", "ilike", f"pipeline-buttonaction-{model}-{self.id}"),
                ("model", "=", model),
            ]
        ).unlink()

    def add_fileupload_wizard(self):
        self = self.sudo()
        window_act = self.env["ir.actions.act_window"].create(
            {
                "res_model": "zbs.wiz.fileupload",
                "target": "new",
                "context": "{'default_pipeline_id': %s}" % self.id,
                "view_mode": "form",
                "pipeline_id": self.id,
            }
        )
        mi = self.env["ir.ui.menu"].create(
            {
                "name": f"{self.name} File Upload",
                "parent_id": self.parent_menu_id.id,
                "action": f"{window_act._name},{window_act.id}",
                "pipeline_id": self.id,
            }
        )
        self.created_window_action_ids = [(4, window_act.id)]
        self.created_menu_item_ids = [(4, mi.id)]
