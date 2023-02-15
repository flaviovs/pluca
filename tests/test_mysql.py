import os
import unittest
from typing import Any

import pluca
import pluca.sql
from pluca.test import CacheTester

_host = os.getenv('MYSQL_HOST')
_db = os.getenv('MYSQL_DATABASE')


class TestMysql(CacheTester, unittest.TestCase):

    def setUp(self) -> None:

        if not (_host and _db):
            raise unittest.SkipTest('MYSQL_* environment variables not set')

        try:
            import mysql.connector  # pylint: disable=import-outside-toplevel
        except ModuleNotFoundError as ex:
            raise unittest.SkipTest(str(ex)) from ex
        self._conn = mysql.connector.connect(user='root',
                                             host=_host,
                                             database=_db,
                                             use_pure=True)

    def tearDown(self) -> None:
        self._conn.close()

    def get_cache(self) -> pluca.Cache:
        self._create_table(self._conn)
        return pluca.sql.Cache(self._conn)

    def _create_table(self,  # pylint: disable=too-many-arguments
                      conn: Any,
                      table: str = 'cache',
                      k_col: str = 'k',
                      v_col: str = 'v',
                      exp_col: str = 'expires') -> None:
        cur = conn.cursor()
        cur.execute(f'DROP TABLE IF EXISTS {table}')
        cur.execute(f'CREATE TABLE {table} ('
                    f'{k_col} VARCHAR(40) PRIMARY KEY, '
                    f'{v_col} BLOB NOT NULL, '
                    f'{exp_col} DOUBLE'
                    ')')
        cur.close()
