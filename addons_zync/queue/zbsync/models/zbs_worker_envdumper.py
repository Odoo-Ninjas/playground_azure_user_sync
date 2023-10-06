from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class InstanceEnvDumper(models.Model):
    _inherit = "zbs.worker"
    _name = "zbs.instance.env.dumper"

    line_ids = fields.One2many(
        "zbs.instance.env.dumper.line", "env_dumper_id", string="Lines"
    )

    def process(self, instance, data):
        env = instance._get_env()
        globals = env._d
        globals["data"] = data
        for line in self.line_ids:
            value = self.env["zbs.tools"].exec_get_result(line.code, globals)
            env[line.key] = value
        instance._set_env(env)
        return instance.Result(data)


class InstanceEnvDumperLine(models.Model):
    _inherit = ["zbs.xport.mixin"]
    _name = "zbs.instance.env.dumper.line"

    env_dumper_id = fields.Many2one("zbs.instance.env.dumper")
    key = fields.Char("Key")
    code = fields.Char("Code")
