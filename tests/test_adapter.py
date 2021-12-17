import unittest
from unittest.mock import Mock, call

import pluca


class CacheAdapter(pluca.CacheAdapter):
    pass


CacheAdapter.__abstractmethods__ = set()  # type: ignore


class TestAdapter(unittest.TestCase):

    def test_has(self):
        a = CacheAdapter()

        a.get = Mock(return_value=True)
        self.assertTrue(a.has('key'))

        a.get.side_effect = KeyError
        self.assertFalse(a.has('key'))

    def test_put_many(self):
        a = CacheAdapter()

        a.put = Mock()
        a.put_many([('k1', 1), ('k2', 2)], 10)

        self.assertListEqual(a.put.call_args_list,
                             [call('k1', 1, 10), call('k2', 2, 10)])

    def test_get_many(self):
        a = CacheAdapter()

        a.get = Mock()
        a.get_many(['k1', 'k2'])

        self.assertListEqual(a.get.call_args_list, [call('k1'), call('k2')])

    def test_loads(self):
        a = CacheAdapter()

        data = (1, 3.1415, False, None, {'a': 1}, (7, 8, 9), {10, 20})

        self.assertEqual(a._loads(a._dumps(data)), data)

    def test_get_cache_key(self):
        a = CacheAdapter()
        self.assertEqual(a._get_cache_key('pluca is great'),
                         '6e2c6ac95cedbd453d0eb9b1625abb6d')

    def test_get_cache_complex_key(self):
        a = CacheAdapter()
        self.assertEqual(a._get_cache_key(('test', 1, False, None, 3.1415)),
                         'c1781abf178798ac9822573b32369829')

    def test_get_cache_key_dict_preserve_order(self):
        a = CacheAdapter()

        key1 = {'a': 1, 'b': 2}
        key2 = {'b': 2, 'a': 1}

        self.assertNotEqual(a._get_cache_key(key1), a._get_cache_key(key2))
