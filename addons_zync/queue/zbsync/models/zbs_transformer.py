from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from .zebrooset import _WrappedDict, _WrappedList


class Transformer(models.AbstractModel):
    _inherit = "zbs.worker"
    _name = "zbs.transformer"
    # execute python code to transform data

    # diret mapping , submappings


class PythonTransformer(models.Model):
    _inherit = "zbs.transformer"
    _name = "zbs.transformer.python"
    _description = "Transformer/Code Executor"

    code = fields.Text("Code", tracking=True)
    propagate_code_result = fields.Boolean(
        "Reduce",
        help="If set, then the result of the code is transported to the next worker",
        tracking=True,
    )

    def _do_exec(self, record, data, index, instance):
        return self.env["zbs.tools"].exec_get_result(
            self.code,
            {
                "data": data,
                "record": record,
                "index": index,
                "instance": instance,
            },
        )

    def process(self, instance, data):
        if self.propagate_code_result:
            result = self._do_exec(data, data, 0, instance)
            return instance.Result(result)
        return super().process(instance, data)

    def process_record(self, instance, index, record, data):
        return self._do_exec(record, data, index, instance)
