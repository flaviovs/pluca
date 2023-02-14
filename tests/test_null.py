import unittest

import pluca
import pluca.null
from pluca.test import CacheTester


class TestNull(CacheTester, unittest.TestCase):

    def get_cache(self) -> pluca.Cache:
        return pluca.null.Cache()

    # Override CacheTester tests for the null cache use case.

    def test_put_get(self) -> None:
        cache = self.get_cache()
        cache.put('k1', 'v1')
        cache.put('k2', 'v2')
        with self.assertRaises(KeyError):
            cache.get('k1')
        with self.assertRaises(KeyError):
            cache.get('k2')

    def test_get_default(self) -> None:
        cache = self.get_cache()
        self.assertEqual(cache.get('nonexistent', 'default'), 'default')

    def test_remove(self) -> None:
        cache = self.get_cache()
        cache.put('k', 'v')
        with self.assertRaises(KeyError):
            cache.get('k')
        with self.assertRaises(KeyError):
            cache.get('nonexistent')

    def test_has(self) -> None:
        cache = self.get_cache()
        cache.put('k', 'v')
        self.assertFalse(cache.has('k'))
        self.assertFalse(cache.has('nonexistent'))

    def test_put_many(self) -> None:
        cache = self.get_cache()
        cache.put_many({'k1': 1, 'k2': 2})
        with self.assertRaises(KeyError):
            cache.get('k1')
        with self.assertRaises(KeyError):
            cache.get('k2')

    def test_get_many(self) -> None:
        cache = self.get_cache()
        cache.put('k', 'v')
        values = cache.get_many(['k'])
        self.assertNotIn('k', values)

    def test_get_many_default(self) -> None:
        cache = self.get_cache()
        cache.put('k', 'v')
        values = cache.get_many(['k'], 'default')
        self.assertEqual(values, [('k', 'default')])

    def _pass(self) -> None:
        pass

    test_put_get_check_key_types = _pass
    test_put_tuple_key = _pass
    test_put_list_key = _pass
    test_put_dict_key = _pass
    test_get_many_default_none = _pass
    test_decorator = _pass
