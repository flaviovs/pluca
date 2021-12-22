import sys
import unittest
from unittest.mock import Mock

from pluca import Cache
import pluca.cache as plc
import pluca.memory


class TestCache(unittest.TestCase):

    def setUp(self):
        # Make sure that pluca standard adapters used are unloaded
        # before tests.
        for mod in ('pluca.file', 'pluca.null'):
            try:
                del sys.modules[mod]
            except KeyError:
                pass

    def test_add_get(self):
        plc.add('test_add_get', 'pluca.file.create')

        cache = plc.get('test_add_get')
        self.assertIsInstance(cache, Cache)

        import pluca.file
        self.assertIsInstance(cache.adapter, pluca.file.CacheAdapter)

    def test_add_callback(self):
        cb = Mock()
        plc.add('test_add_callback', cb)
        self.assertEqual(cb.call_count, 1)

    def test_add_dup_name(self):
        plc.add('test_add_dup_name', 'pluca.null.create')
        with self.assertRaises(ValueError):
            plc.add('test_add_dup_name', 'pluca.null.create')

    def test_remove(self):
        plc.add('test_remove', 'pluca.null.create')
        plc.remove('test_remove')
        with self.assertRaises(KeyError):
            plc.get('test_remove')

    def test_remove_all(self):
        plc.add('test_remove_all_1', 'pluca.null.create')
        plc.add('test_remove_all_2', 'pluca.null.create')
        plc.add('test_remove_all_3', 'pluca.null.create')

        plc.remove_all()

        with self.assertRaises(KeyError):
            plc.get('test_remove_all_1')
        with self.assertRaises(KeyError):
            plc.get('test_remove_all_2')
        with self.assertRaises(KeyError):
            plc.get('test_remove_all_3')

    def test_basic_config(self):
        plc.basic_config()

        cache = plc.get()
        self.assertIsInstance(cache, Cache)

        import pluca.file
        self.assertIsInstance(cache.adapter, pluca.file.CacheAdapter)

    def test_get_default_calls_basic_config(self):
        plc.remove_all()
        cache = plc.get()
        self.assertIsInstance(cache, Cache)

        import pluca.file
        self.assertIsInstance(cache.adapter, pluca.file.CacheAdapter)

    def test_decorator(self):
        cache = pluca.memory.create()

        calls = 0

        def func(a, b, c):
            nonlocal calls
            calls += 1
            return a + b + c

        dec = cache(func)

        res1 = dec(1, 2, 3)
        self.assertEqual(res1, 1 + 2 + 3)
        self.assertEqual(1, calls)

        res2 = dec(1, 2, 3)
        self.assertEqual(res2, 1 + 2 + 3)
        self.assertEqual(1, calls)  # NB: cached result.

        res3 = dec(a=1, b=2, c=3)
        self.assertEqual(res3, 1 + 2 + 3)
        self.assertEqual(2, calls)

        # Ensure that order of kwargs does not matter.
        res4 = dec(c=3, a=1, b=2)
        self.assertEqual(res4, 1 + 2 + 3)
        self.assertEqual(2, calls)
