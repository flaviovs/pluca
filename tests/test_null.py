import unittest

import pluca
from pluca.null import create
from pluca.test import CacheTester


class TestNull(CacheTester, unittest.TestCase):

    def get_cache(self) -> pluca.Cache:
        return create()

    # Override CacheTester tests for the null cache use case.

    def test_put_get(self) -> None:
        c = self.get_cache()
        c.put('k1', 'v1')
        c.put('k2', 'v2')
        with self.assertRaises(KeyError):
            c.get('k1')
        with self.assertRaises(KeyError):
            c.get('k2')

    def test_get_default(self) -> None:
        c = self.get_cache()
        self.assertEqual(c.get('nonexistent', 'default'), 'default')

    def test_remove(self) -> None:
        c = self.get_cache()
        c.put('k', 'v')
        with self.assertRaises(KeyError):
            c.get('k')
        with self.assertRaises(KeyError):
            c.get('nonexistent')

    def test_has(self) -> None:
        c = self.get_cache()
        c.put('k', 'v')
        self.assertFalse(c.has('k'))
        self.assertFalse(c.has('nonexistent'))

    def test_put_many(self) -> None:
        c = self.get_cache()
        c.put_many({'k1': 1, 'k2': 2})
        with self.assertRaises(KeyError):
            c.get('k1')
        with self.assertRaises(KeyError):
            c.get('k2')

    def test_get_many(self) -> None:
        c = self.get_cache()
        c.put('k', 'v')
        values = c.get_many(['k'])
        self.assertNotIn('k', values)

    def test_get_many_default(self) -> None:
        c = self.get_cache()
        c.put('k', 'v')
        values = c.get_many(['k'], 'default')
        self.assertEqual(values, [('k', 'default')])

    def _pass(self) -> None:
        pass

    test_put_get_check_key_types = _pass
    test_put_tuple_key = _pass
    test_put_list_key = _pass
    test_put_dict_key = _pass
