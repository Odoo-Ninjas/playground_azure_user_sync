from odoo import _, api, fields, models, SUPERUSER_ID
import traceback
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools.sql import table_exists
from odoo.tools.safe_eval import safe_eval
import inspect
from collections import defaultdict
import logging
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger("method_hook.trigger")


class TriggerMethodHook(models.AbstractModel):
    _name = "method_hook.trigger.mixin"

    domain = fields.Char("Domain", required=True, default="[]")
    method = fields.Char("Method", required=True)
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
    )
    link_expression = fields.Char("Link Expression", default="object")

    def _trigger(self, instance, args):
        breakpoint()
        raise NotImplementedError("Implement hook!")

    def _eval_linkexpression(self, object):
        if not self.link_expression:
            return object
        recs = safe_eval(
            self.link_expression,
            dict(
            obj=object,
            object=object,
            objects=object)
        )
        return recs

    @api.model
    def create(self, vals):
        result = super().create(vals)
        self._check_method()
        self._update_registry()
        return result

    def write(self, vals):
        result = super().write(vals)
        self._check_method()
        self._update_registry()
        return result

    def unlink(self):
        result = super().unlink()
        self._update_registry()
        return result

    @api.constrains("method")
    def _check_method(self):
        for rec in self:
            if not rec.method:
                continue
            obj = self.env.get(rec.model_id.model)
            if obj is None:
                raise ValidationError((f"Object not found: {rec.model_id.model}."))
            if not getattr(obj, rec.method, None):
                raise ValidationError(
                    (f"Could not find {rec.method} on {rec.model_id.model}.")
                )

    @api.model
    def _update_registry(self):
        self.pool.registry_invalidated = True
        self.pool.signal_changes()
        self._register_hook()

    def _register_hook(self):
        if (
            not table_exists(self.env.cr, self._table)
            or self._name == "method_hook.trigger.mixin"
        ):
            return

        def make_hook(trigger_model, obj, model_id, method):
            """Instanciate a create method that processes action rules."""

            def is_model_function():
                # TODO: __wrapped__ not set
                # surely better way to retrieve @api.model situation
                # https://stackoverflow.com/questions/43506378/how-to-get-source-code-of-function-that-is-wrapped-by-a-decorator
                func = getattr(obj, method)
                src = inspect.getsource(func).split("def")[0]
                return "@api.model" in src

            def _trigger_hook(self, args_packed):
                for hook in (
                    self.env[trigger_model]
                    .sudo()
                    .search(
                        [
                            ("model_id", "=", model_id),
                            ("method", "=", method),
                        ]
                    )
                ):
                    domain = safe_eval(hook.domain)
                    recordset = self
                    if domain:
                        recordset = recordset.filtered_domain(domain)
                    for rec in recordset:
                        linkedrecords = hook._eval_linkexpression(rec)
                        for linkedrecord in linkedrecords:
                            hook._trigger(linkedrecord, args_packed, hook.method)
            
            def _pack_args(args, kwargs):
                return {'args': args, 'kwargs': kwargs}

            # Make sure that for write and create the first argument is always
            # the vals (not kwargs), so that all that depend on this have the 
            # same interface

            @api.model_create_multi
            def patched_create(self, vals_list, **kw):
                result = patched_create.origin(self, vals_list, **kw)
                for i, record in enumerate(result):
                    vals = vals_list[i]
                    _trigger_hook(record, _pack_args([vals], kw))
                return result

            def patched_write(self, vals, **kw):
                result = patched_write.origin(self, vals, **kw)
                for record in self:
                    _trigger_hook(record, _pack_args([vals], kw))
                return result

            @api.model
            def patched_model(self, *args, **kwargs):
                result = patched_model.origin(self, *args, **kwargs)
                _trigger_hook(self, _pack_args(args, kwargs))
                return result

            def patched(self, *args, **kwargs):
                result = patched.origin(self, *args, **kwargs)
                _trigger_hook(self, _pack_args(args, kwargs))
                return result

            if method == "create":
                return patched_create
            elif method == "write":
                return patched_write
            elif is_model_function():
                return patched_model
            else:
                return patched

        patched_funcs = defaultdict(set)

        def patch(obj, method_name, method):
            """Patch method `name` on `model`, unless it has been patched already."""

            if obj._name not in patched_funcs[method_name]:
                patched_funcs[method_name].add(obj._name)
                obj._patch_method(method_name, method)

        # retrieve all actions, and patch their corresponding model
        for hook in self.search([]):
            obj = self.env.get(hook.model_id.model)

            # Do not crash if the model of the base_action_rule was uninstalled
            if obj is None:
                _logger.warning(
                    (
                        f"Check Method with ID {hook.modeld_id.id} depends "
                        f"on model {hook.model_id.model} "
                        f"on flow {hook.flow_id.name}"
                    )
                )
                continue

            if getattr(obj, hook.method, None):
                patch(obj, hook.method, make_hook(self._name, obj, hook.model_id.id, hook.method))
