import re
import threading
from odoo import registry
from odoo import _, api, models
import hashlib
import struct
from contextlib import contextmanager
from odoo.addons.queue_job.exception import RetryableJobError
from odoo.exceptions import ValidationError


def get_subclasses(env, parent_class_name, ignore=None):
    """
    Returns the inherited classes of a class
    """

    def _fetch(parent):
        for x in list(parent._inherit_children) + list(parent._inherits_children):
            yield x
            try:
                env[x]
            except KeyError:
                continue
            yield from _fetch(env[x])

    res = set()
    for x in _fetch(env[parent_class_name]):
        res.add(x)
    return res


class zbs_tools(models.AbstractModel):
    _name = "zbs.tools"

    @api.model
    def zebrooset(self, data):
        from .zebrooset import ZebrooSet

        return ZebrooSet(data)

    @api.model
    def _get_subclasses(self, model):
        subclasses = get_subclasses(self.env, model)
        return subclasses

    @api.model
    def pg_advisory_lock(self, lock):
        hasher = hashlib.sha1(str(lock).encode())
        int_lock = struct.unpack("q", hasher.digest()[:8])
        func = "pg_try_advisory_xact_lock"
        self.env.cr.execute(f"SELECT {func}(%s);", (int_lock,))

        try:
            acquired = self.env.cr.fetchone()[0]
            if not acquired:
                raise RetryableJobError(
                    f"Could not acquire advisory lock on {lock} [{int_lock}]",
                    seconds=3,
                    ignore_retry=True,
                )

        except Exception as ex:
            raise RetryableJobError(
                f"Could not acquire advisory lock on {lock} [{int_lock}]",
                seconds=3,
                ignore_retry=True,
            ) from ex
        return acquired

    @api.model
    @contextmanager
    def pglock(self, name):
        self.env["zbs.tools"].pg_advisory_lock(name)
        yield

    @api.model
    def pg_advisory_lock_keyvalues(self, extra_string, key_values):
        vals = []
        for key in sorted(key_values):
            vals.append((key, key_values[key]))
        vals = (extra_string or "") + str(vals)
        return self.pg_advisory_lock(vals)

    @api.model
    def exec_get_result(self, code, globals_dict):
        if not code:
            raise ValidationError("Code missing")
        from copy import deepcopy

        dict2 = {k: v for (k, v) in globals_dict.items()}
        del globals_dict

        if self.env.context.get("instance"):
            dict2 = (
                self.env.context.get("instance")
                .with_context(self.env.context)
                ._get_default_objects(dict2)
            )
        else:
            dict2['env'] = self.env

        code = (code or "").strip()
        code = code.splitlines()
        if code and code[-1].startswith(" ") or code[-1].startswith("\t"):
            code.append("True")
        code[-1] = "return " + code[-1] if not code[-1].startswith("return ") else code[-1]
        code = "\n".join(["  " + x for x in code])
        keys = ",".join(list(dict2.keys()))
        wrapper = (
            f"def __wrap({keys}):\n"
            f"{code}\n\n"
            f"result_dict['result'] = __wrap({keys})"
        )
        result_dict = {}
        dict2["result_dict"] = result_dict
        exec(wrapper, dict2)
        return result_dict.get("result")

    @api.model
    def _is_testing(self):
        thread = threading.current_thread()
        return getattr(thread, "testing", False)

    @api.model
    @contextmanager
    def new_env(self, on_after_commit=None):
        su = self.env.su
        if self._is_testing():
            yield self.env
        else:
            db_registry = registry(self.env.cr.dbname)
            with api.Environment.manage():
                with db_registry.cursor() as cr:
                    env = api.Environment(cr, self.env.user.id, {}, su)
                    yield env
                    env["zbs.tools"].flush()
                    cr.commit()
                    if on_after_commit:
                        on_after_commit()

    @api.model
    def with_delay(self, instance, enabled=True, *args, **kwargs):
        return instance

    @api.model
    def commit(self):
        if not self._is_testing():
            self.env.cr.commit()

    def flush(self, rec=None):
        if rec:
            if hasattr(rec, "flush_recordset"):
                # V16
                rec.flush_recordset()
            else:
                rec.flush()
        else:
            if hasattr(self.env, "flush_all"):
                self.env.flush_all()
            else:
                self.env["base"].flush()
