import unittest

import pluca
import pluca.memory
from pluca.test import CacheTester


class TestMemory(CacheTester, unittest.TestCase):

    def get_cache(self) -> pluca.Cache:
        return pluca.memory.Cache()

    def test_max_entries(self) -> None:
        cache = pluca.memory.Cache(max_entries=3)

        cache.put('key1', 1, 10)  # Earliest expiration, will be removed.
        cache.put('key2', 2)
        cache.put('key3', 3)
        cache.put('key4', 1, 20)

        self.assertTrue(cache.has('key4'))
        self.assertTrue(cache.has('key3'))
        self.assertTrue(cache.has('key2'))
        self.assertFalse(cache.has('key1'))

    def test_gc(self) -> None:
        cache = pluca.memory.Cache(max_entries=2)

        cache.put('key1', 1)
        cache.put('key2', 2)
        cache.put('key3', 3)

        cache.gc()

        self.assertTrue(cache.has('key3'))
        self.assertTrue(cache.has('key2'))
        self.assertFalse(cache.has('key1'))

    def test_constructor_validation(self) -> None:
        with self.assertRaises(ValueError):
            pluca.memory.Cache(max_entries=2, prune=3)

    def test_copy_data(self) -> None:
        cache = pluca.memory.Cache()

        alist = [1, 2, 3]

        cache.put('alist', alist)

        alist[1] = 20

        self.assertEqual(cache.get('alist'), [1, 2, 3])
