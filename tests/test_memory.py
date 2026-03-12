import unittest

import pluca
import pluca.memory
from pluca.test import AdapterTester


class TestMemory(AdapterTester, unittest.TestCase):

    def get_adapter(self) -> pluca.memory.Adapter:
        return pluca.memory.Adapter()

    def test_max_entries(self) -> None:
        cache = pluca.Cache(pluca.memory.Adapter(max_entries=3))

        cache.put('key1', 1, 10)  # Earliest expiration, will be removed.
        cache.put('key2', 2)
        cache.put('key3', 3)
        cache.put('key4', 1, 20)

        self.assertTrue(cache.has('key4'))
        self.assertTrue(cache.has('key3'))
        self.assertTrue(cache.has('key2'))
        self.assertFalse(cache.has('key1'))

    def test_gc(self) -> None:
        cache = pluca.Cache(pluca.memory.Adapter(max_entries=2))

        cache.put('key1', 1)
        cache.put('key2', 2)
        cache.put('key3', 3)

        cache.gc()

        self.assertTrue(cache.has('key3'))
        self.assertTrue(cache.has('key2'))
        self.assertFalse(cache.has('key1'))

    def test_constructor_validation(self) -> None:
        with self.assertRaises(ValueError):
            pluca.memory.Adapter(max_entries=2, prune=3)

    def test_copy_data(self) -> None:
        cache = pluca.Cache(pluca.memory.Adapter())

        alist = [1, 2, 3]

        cache.put('alist', alist)

        alist[1] = 20

        self.assertEqual(cache.get('alist'), [1, 2, 3])

    def test_put_max_age_zero(self) -> None:
        cache = pluca.Cache(pluca.memory.Adapter())
        cache.put('foo', 'bar', max_age=0)
        with self.assertRaises(KeyError):
            cache.get('foo')
