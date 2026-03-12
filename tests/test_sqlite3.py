import unittest
import sqlite3
import tempfile
from typing import Any

import pluca
import pluca.sqlite3
from pluca.test import AdapterTester


class _Undumpable:

    def __reduce__(self) -> tuple[object, tuple[Any, ...]]:
        raise TypeError('cannot pickle _Undumpable')


class TestSqlite3BackEnd(AdapterTester, unittest.TestCase):

    def get_adapter(self) -> pluca.sqlite3.Adapter:
        return pluca.sqlite3.Adapter(':memory:')

    def test_put_max_age_zero(self) -> None:
        cache = self.get_cache()
        cache.put('foo', 'bar', max_age=0)
        with self.assertRaises(KeyError):
            cache.get('foo')

    def test_pragma(self) -> None:
        with self.assertRaises(sqlite3.OperationalError) as ex:
            pluca.Cache(pluca.sqlite3.Adapter(':memory:',
                                              pragma={'query_only': True}))
        self.assertIn('readonly database', str(ex.exception))

        # Check pragma string handling.
        pluca.Cache(pluca.sqlite3.Adapter(':memory:',
                                          pragma={'encoding': 'utf-8'}))

    def test_pragma_invalid_identifier(self) -> None:
        expected_error = 'Invalid SQLite PRAGMA ' \
            'identifier'
        invalid_names = (
            'query-only',
            'query only',
            'query;drop',
            '"query_only"',
            '1query_only',
            '',
        )
        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError,
                                            expected_error):
                    pluca.Cache(pluca.sqlite3.Adapter(
                        ':memory:',
                        pragma={name: True},
                    ))

    def test_pragma_valid_identifier(self) -> None:
        cache = pluca.Cache(pluca.sqlite3.Adapter(':memory:',
                                                  pragma={
                                                      'journal_mode': 'WAL'}))
        cache.put('foo', 'bar')
        self.assertEqual(cache.get('foo'), 'bar')

    def test_put_persists(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            cache.put('foo', 'bar')
            cache.shutdown()
            del cache

            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            self.assertEqual(cache.get('foo'), 'bar')

    def test_put_many_persists(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            cache.put_many({'foo': 'bar', 'zee': 'lee'})
            cache.shutdown()
            del cache

            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            self.assertEqual(cache.get('foo'), 'bar')
            self.assertEqual(cache.get('zee'), 'lee')

    def test_put_many_is_atomic(self) -> None:
        cache = self.get_cache()

        with self.assertRaises(TypeError):
            cache.put_many([('ok', 'value'), ('boom', _Undumpable())])

        with self.assertRaises(KeyError):
            cache.get('ok')

    def test_put_many_is_atomic_with_autocommit(self) -> None:
        cache = pluca.Cache(pluca.sqlite3.Adapter(':memory:',
                                                  isolation_level=None))

        with self.assertRaises(TypeError):
            cache.put_many([('ok', 'value'), ('boom', _Undumpable())])

        with self.assertRaises(KeyError):
            cache.get('ok')

    def test_table_is_created_without_rowid(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            row = cache._conn.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = 'cache'"
            ).fetchone()

            self.assertIsNotNone(row)
            self.assertIn('WITHOUT ROWID', row[0].upper())

    def test_remove_persists(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            cache.put('foo', 'bar')
            cache.remove('foo')
            cache.shutdown()
            del cache

            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            with self.assertRaises(KeyError):
                cache.get('foo')

    def test_remove_many_persists(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            cache.put('foo', 'bar')
            cache.put('xii', 'lee')
            cache.remove_many(['foo', 'xii'])
            cache.shutdown()
            del cache

            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            with self.assertRaises(KeyError):
                cache.get('foo')
            with self.assertRaises(KeyError):
                cache.get('xii')

    def test_remove_many_empty_iterables(self) -> None:
        cache = self.get_cache()

        cache.put('foo', 'bar')

        cache.remove_many([])
        cache.remove_many(())
        cache.remove_many(iter(()))

        self.assertEqual(cache.get('foo'), 'bar')

    def test_get_many_empty_iterables(self) -> None:
        cache = self.get_cache()

        self.assertEqual(cache.get_many([]), [])
        self.assertEqual(cache.get_many(()), [])
        self.assertEqual(cache.get_many(iter(())), [])
        self.assertEqual(cache.get_many([], default='default'), [])

    def test_flush_persists(self) -> None:
        with tempfile.NamedTemporaryFile() as ctx:
            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            cache.put('foo', 'bar')
            cache.flush()
            cache.shutdown()
            del cache

            cache = pluca.Cache(pluca.sqlite3.Adapter(ctx.name))
            with self.assertRaises(KeyError):
                cache.get('foo')
