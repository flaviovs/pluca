import unittest
import sqlite3

import pluca
import pluca.sql
from pluca.test import CacheTester


class TestSqlite3(CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        self._conn = sqlite3.connect(':memory:')

    def tearDown(self) -> None:
        self._conn.close()

    def get_cache(self) -> pluca.sql.Cache:
        self._create_table(self._conn)
        return pluca.sql.Cache(self._conn)

    def _create_table(self,  # pylint: disable=too-many-arguments
                      conn: sqlite3.Connection,
                      table: str = 'cache',
                      k_col: str = 'k',
                      v_col: str = 'v',
                      exp_col: str = 'expires') -> None:
        conn.execute(f'CREATE TABLE {table} ('
                     f'{k_col} TEXT PRIMARY KEY, '
                     f'{v_col} BLOB NOT NULL, '
                     f'{exp_col} FLOAT'
                     ')')
