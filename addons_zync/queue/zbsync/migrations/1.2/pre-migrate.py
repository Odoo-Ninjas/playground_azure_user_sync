from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    cr.execute("select state from zbs_instance where state = 'running'")
    if cr.fetchall():
        raise Exception(
            "Cannot update - please make sure all instances are done or failed"
        )
    cr.execute("delete from zbs_instance;")
    cr.execute("delete from zbs_instance_logs;")

    # env = api.Environment(cr, SUPERUSER_ID, {})
    # cr.execute("alter table zbs_instance_logs add output_data_temp text;")

    # cr.execute("delete from zbs_instance_line where instance_id is null;")

    # cr.execute("alter table zbs_instance_logs add column line_id_temp int ")
    # cr.execute("update zbs_instance_logs set line_id_temp=instance_line_id")
