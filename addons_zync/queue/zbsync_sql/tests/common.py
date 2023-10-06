import os
from passlib.context import CryptContext
import json
import os
import pprint
import logging
import time
import uuid
from datetime import datetime, timedelta
from unittest import skipIf
from odoo import api
from odoo import fields
from odoo.tests.common import TransactionCase, Form
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, RedirectWarning, ValidationError, AccessError
from odoo.addons.zbsync.tests.test_pipe import ZBSPipelineCase


class SqlTest(ZBSPipelineCase):
    def _get_connection(self):
        conn = self.env["zbs.connection.sql"].create(
            {
                "name": "local",
                "type": "postgres",
                "dbname": self.env.cr.dbname,
                "host": os.getenv("DB_HOST"),
                "port": os.getenv("DB_PORT"),
                "username": os.getenv("DB_USER"),
                "password": os.getenv("DB_PWD"),
            }
        )
        return conn

    def _get_odbc_postgres_connection(self):
        conn = self.env["zbs.connection.sql"].create(
            {
                "name": "localodbc",
                "type": "odbc",
                "connstring": (
                    # "DRIVER={{PostgreSQL Unicode}};"
                    "DRIVER={{/usr/lib/aarch64-linux-gnu/odbc/psqlodbcw.so}};"
                    "SERVER={hostname};"
                    "DATABASE={dbname};"
                    "UID={username};"
                    "PWD={password};"
                    "PORT={port};"
                ),
                "dbname": self.env.cr.dbname,
                "host": os.getenv("DB_HOST"),
                "port": os.getenv("DB_PORT"),
                "username": os.getenv("DB_USER"),
                "password": os.getenv("DB_PWD"),
            }
        )
        return conn