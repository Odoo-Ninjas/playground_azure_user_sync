import time
import os
import configparser
from pathlib import Path
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import psycopg2
import pymysql
import pymssql
from odoo.addons.zbsync.exceptions import ConfigurationError
from contextlib import contextmanager
from .expression import WhereExpression
from datetime import datetime, timedelta
from odoo.addons.queue_job.exception import JobError, RetryableJobError
import logging

logger = logging.getLogger("ZYNC SQL CONNECTION")

class HasSqlConnection(models.AbstractModel):
    _name = "zbs.sql.connection.mixin"
    _description = "Mixin for sql connection based models like grabbers and dumpers"

    connection_id = fields.Many2one("zbs.connection.sql", string="Connection")


class SqlConnection(models.Model):
    _inherit = [
        "zbs.connection",
        "zbs.connection.mixin.usernamepassword",
        "zbs.connection.mixin.hostport",
    ]
    _name = "zbs.connection.sql"
    _description = "Connection to an sql database"

    timeout = fields.Integer("Timeout", default=120)

    port = fields.Integer(default=8069)
    dbname = fields.Char("DBName")
    password = fields.Char(required=False)
    type = fields.Selection(
        [
            ("postgres", "Postgres"),
            ("mssql", "MSSQL"),
            ("mysql", "MYSQL"),
            ("odbc", "ODBC"),
        ],
        string="Type",
    )
    connstring = fields.Char(
        "Driver",
        default="ODBC Connectionstring with  {password} {username} {dbname} {hostname}",
    )

    use_transaction = fields.Boolean("Use Transaction", default=True)
    begin_transaction = fields.Text("Begin Transaction", default="BEGIN TRANSACTION")
    commit_transaction = fields.Text("Commit Transaction", default="COMMIT TRANSACTION")
    rollback_transaction = fields.Text("Rollback Transaction", default="BEGIN TRANSACTION")

    @property
    def placeholder(self):
        return WhereExpression.parameter(self.type)

    @api.onchange("type")
    def onchange_type(self):
        if self.type == "postgres":
            self.port = 5432
        elif self.type == "mssql":
            self.port = 1433
        elif self.type == "mssql":
            self.port = 3306

    @contextmanager
    def _get_conn(self):
        self.ensure_one()
        conn, cr = self._get_object()
        try:
            yield cr
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _get_object(self):
        if self.type == "mssql":
            conn, cr = self._get_object_mssql()
        elif self.type == "postgres":
            conn, cr = self._get_object_postgres()
        elif self.type == "mysql":
            conn, cr = self._get_object_mysql()
        elif self.type == "odbc":
            conn, cr = self._get_object_odbc()
        else:
            raise NotImplementedError(self.type)

        self._before_conn(cr)
        return conn, cr

    def _before_conn(self, cr):
        if self.type in ['postgres', 'mssql']:
            cr.execute("BEGIN TRANSACTION;")

    def _get_object_mssql(self):
        conn = pymssql.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            database=self.dbname,
            timeout=self.timeout,
        )
        cr = conn.cursor(as_dict=True)
        cr.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
        return conn, cr

    def _get_object_mysql(self):
        conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            database=self.dbname,
            timeout=self.timeout,
        )
        cr = conn.cursor(as_dict=True)
        return conn, cr

    def _get_object_postgres(self):
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            database=self.dbname,
            timeout=self.timeout,
        )
        cr = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return conn, cr

    def _get_object_odbc(self):
        conn_str = self.connstring
        conn_str = conn_str.format(
            username=self.username,
            uid=self.username,
            pwd=self.password,
            password=self.password,
            passwd=self.password,
            hostname=self.host,
            host=self.host,
            server=self.host,
            port=self.port,
            database=self.dbname,
            dbname=self.dbname,
            timeout=self.timeout,
        )
        import pyodbc
        conn = pyodbc.connect(conn_str)
        cr = conn.cursor()
        return conn, cr

    def _has_to_dict(self):
        self.ensure_one()
        return self.type in ['odbc']

    def fetchall(self, cr, sql, params, batchsize=1000):
        self.execute(cr, sql, params)
        recs = []
        while True:
            # if fetchall with big records then outofmemory possible;
            # was more robust by that
            chunk = cr.fetchmany(batchsize)
            if not chunk:
                break
            recs += chunk
        if self._has_to_dict():
            recs = list(self._make_dict(cr, recs))
        return recs

    def _make_dict(self, cr, result):
        column_names = [column[0] for column in cr.description]
        for row in result:
            yield dict(zip(column_names, row))

    @contextmanager
    def _in_transaction(self, cr, table=None):
        def _run_sql(sql):
            sql = sql.format(table=table)
            cr.execute(sql)

        try:
            # if statement is for example LOCK TABLE
            # there may happen errors
            if self.use_transaction:
                _run_sql(self.begin_transaction)
        except Exception as ex:
            raise RetryableJobError(
                str(ex),
                ignore_retry=True,
                seconds=10,
            ) from ex

        try:
            yield cr
            _run_sql(self.commit_transaction)
        except:
            _run_sql(self.rollback_transaction)
            raise