from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    return
    cr.execute("select id from zbs_instance_line ")
    for line in cr.fetchall():
        line_id = line[0]
        cr.execute(
            (
                "select state from zbs_instance where id in "
                "(select instance_id from zbs_instance_line where id = %s)"
            ),
            (line_id,),
        )
        instance = cr.fetchone()
        cr.execute(
            "insert into zbs_instance_line_batch(line_id, state) values(%s, %s)",
            (line_id, instance[0]),
        )
        cr.execute("select max(id) from zbs_instance_line_batch")
        batch_id = cr.fetchone()[0]
        cr.execute(
            "update zbs_instance_logs set batch_id=%s where line_id_temp=%s",
            (batch_id, line_id),
        )
    cr.execute("alter table zbs_instance_logs drop column line_id_temp")

    env = api.Environment(cr, SUPERUSER_ID, {})

    def get_next_line(line):
        if line.worker_id._name == "zbs.stop":
            return self.env["zbs.instance.line"]
        lines = line.instance_id.line_ids.sorted()
        idx = lines.idx.index(line.id)
        return lines[idx + 1]

    def get_prev_line(line):
        if line.worker_id._name == "zbs.start":
            return self.env["zbs.instance.line"]
        lines = line.instance_id.line_ids.sorted()
        idx = lines.ids.index(line.id)
        return lines[idx - 1]

    def get_field(instance, fieldname):
        cr.execute(f"select {fieldname} from {instance._table} where id = {instance.id}")
        return cr.fetchone()[0] 

    for line in env["zbs.instance.line"].search([]):
        if line.worker_id._name == "zbs.start":
            logs = line.batch_ids.log_ids.sorted('id')
            if logs:
                line.instance_id.initial_data = logs[0].output_data
        else:
            prevline = get_prev_line(line)
            if prevline:
                logs = prevline.batch_ids.log_ids.sorted()
                if logs:
                    output_data = get_field(logs[0], 'output_data_temp')
                    line.batch_ids[0].input_data = output_data

            logs = line.batch_ids[0].log_ids
            if logs:
                line.batch_ids[0].output_data = get_field(logs[0], 'output_data_temp')

    for batch in env['zbs.instance.line.batch'].search([]):
        logs = batch.log_ids.sorted()
        if logs:
            batch.err_desc = logs[0].last_exception


    cr.execute("alter table zbs_instance_logs drop column output_data_temp;")