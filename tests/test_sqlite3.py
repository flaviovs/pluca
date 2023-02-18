import unittest
import sqlite3
import tempfile

import pluca
import pluca.sql
import pluca.sqlite3
from pluca.test import CacheTester


class TestSqlBackEnd(CacheTester, unittest.TestCase):

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


class TestSqlite3BackEnd(CacheTester, unittest.TestCase):

    def get_cache(self) -> pluca.sqlite3.Cache:
        return pluca.sqlite3.Cache(':memory:')

    def test_pragma(self) -> None:
        with self.assertRaises(sqlite3.OperationalError) as ex:
            pluca.sqlite3.Cache(':memory:', pragma={'query_only': True})
        self.assertIn('readonly database', str(ex.exception))

        # Check proper repr() handling.
        pluca.sqlite3.Cache(':memory:', pragma={'encoding': 'utf-8'})

    def test_put_persists(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.sqlite3.Cache(ctx.name)
            cache.put('foo', 'bar')
            cache.shutdown()
            del cache

            cache = pluca.sqlite3.Cache(ctx.name)
            self.assertEqual(cache.get('foo'), 'bar')

    def test_put_many_persists(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.sqlite3.Cache(ctx.name)
            cache.put_many({'foo': 'bar', 'zee': 'lee'})
            cache.shutdown()
            del cache

            cache = pluca.sqlite3.Cache(ctx.name)
            self.assertEqual(cache.get('foo'), 'bar')
            self.assertEqual(cache.get('zee'), 'lee')

    def test_remove_persists(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.sqlite3.Cache(ctx.name)
            cache.put('foo', 'bar')
            cache.remove('foo')
            cache.shutdown()
            del cache

            cache = pluca.sqlite3.Cache(ctx.name)
            with self.assertRaises(KeyError):
                cache.get('foo')

    def test_remove_many_persists(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.sqlite3.Cache(ctx.name)
            cache.put('foo', 'bar')
            cache.put('xii', 'lee')
            cache.remove_many(['foo', 'xii'])
            cache.shutdown()
            del cache

            cache = pluca.sqlite3.Cache(ctx.name)
            with self.assertRaises(KeyError):
                cache.get('foo')
            with self.assertRaises(KeyError):
                cache.get('xii')

    def test_flush_persists(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.sqlite3.Cache(ctx.name)
            cache.put('foo', 'bar')
            cache.flush()
            cache.shutdown()
            del cache

            cache = pluca.sqlite3.Cache(ctx.name)
            with self.assertRaises(KeyError):
                cache.get('foo')
