import unittest

from pluca.memory import create
from pluca.test import CacheTester


class TestMemory(unittest.TestCase, CacheTester):

    def get_cache(self):
        return create()

    def test_max_entries(self):
        c = create(max_entries=3)

        c.put('key1', 1, 10)  # Earliest expiration, will be removed.
        c.put('key2', 2)
        c.put('key3', 3)
        c.put('key4', 1, 20)

        self.assertTrue(c.has('key4'))
        self.assertTrue(c.has('key3'))
        self.assertTrue(c.has('key2'))
        self.assertFalse(c.has('key1'))
