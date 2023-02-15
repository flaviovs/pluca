import unittest
from typing import Any

import pluca
import pluca.sql
from pluca.test import CacheTester


class TestPostgres(CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        try:
            # pylint: disable-next=import-outside-toplevel
            import postgresql.driver.dbapi20 as postgresql
        except ModuleNotFoundError as ex:
            raise unittest.SkipTest(str(ex)) from ex
        self._conn = postgresql.connect()

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
        conn.execute(f'DROP TABLE IF EXISTS {table}')
        conn.execute(f'CREATE TABLE {table} ('
                     f'{k_col} VARCHAR(40) PRIMARY KEY, '
                     f'{v_col} BYTEA NOT NULL, '
                     f'{exp_col} FLOAT'
                     ')')
