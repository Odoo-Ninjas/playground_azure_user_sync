# method hook triggers

Allows to hook on method events. You can subclass the abstract class and define 
behaviour on called events.


## Subclassing sample


```
class TriggerMethodHook(models.Model):
    _inherit = "method_hook.trigger.mixin"
    _name = "of.trigger.methodhook"

    trigger_id = fields.Many2one("of.trigger", string="Trigger", ondelete="cascade")

    def _trigger(self, instances, args_packed):
		args, kwargs = args['args'], args['kwargs']
        self.trigger_id._start_by_methodhook(instances)

		# do what you want

```