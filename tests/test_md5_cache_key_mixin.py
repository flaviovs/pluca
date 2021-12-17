import unittest

from pluca import MD5CacheKeyMixin


class TestMD5CacheKeyMixin(unittest.TestCase):

    def test_get_cache_key(self):
        obj = MD5CacheKeyMixin()
        self.assertEqual(obj._get_cache_key('pluca is great'),
                         '6e2c6ac95cedbd453d0eb9b1625abb6d')

    def test_get_cache_key_complex(self):
        obj = MD5CacheKeyMixin()
        self.assertEqual(obj._get_cache_key(('test', 1, False, None, 3.1415)),
                         'c1781abf178798ac9822573b32369829')

    def test_get_cache_key_dict_preserve_order(self):
        obj = MD5CacheKeyMixin()

        key1 = {'a': 1, 'b': 2}
        key2 = {'b': 2, 'a': 1}

        self.assertNotEqual(obj._get_cache_key(key1), obj._get_cache_key(key2))
