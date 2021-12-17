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
