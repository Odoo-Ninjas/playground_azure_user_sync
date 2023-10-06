from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import json
from odoo.tools.safe_eval import safe_eval
from faker import Faker


# constat recordset
class ZBSConst(models.Model):
    _inherit = "zbs.worker"
    _name = "zbs.const"
    _description = "CONST"

    data = fields.Text("Data (JSON)")

    demo_count = fields.Integer("Demo Count")

    def make_demo(self):
        fake = Faker()
        for rec in self:
            data = []
            for i in range(rec.demo_count):
                data.append(
                    {
                        "name": fake.name(),
                        "street": fake.address(),
                    }
                )
            rec.data = json.dumps(data, indent=4)

    @api.constrains("data")
    def _updated_data(self):
        for rec in self:
            try:
                data = safe_eval(rec.data)
            except:
                try:
                    data = json.loads(rec.data)
                except:
                    safe_eval(rec.data)

            data = json.dumps(data, indent=4)
            if data != rec.data:
                rec.data = data

    def process(self, instance, data):
        input_data = data
        data = json.loads(self.data or "{}")
        pipeline = self.env.context['pipeline']
        pipeline.log(f"Returning: {data}", "debug")

        for index, record in self._iterate_data(data):
            kept = self._keep_input(index, record, input_data)
            if kept:
                record._merge(kept)
        return instance.Result(self.env["zebrooset"].rs(data))
