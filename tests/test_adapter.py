import unittest
from unittest.mock import Mock, call

import pluca


class CacheAdapter(pluca.CacheAdapter):
    pass


class _AlternateString(str):
    pass


CacheAdapter.__abstractmethods__ = set()  # type: ignore


class TestAdapter(unittest.TestCase):

    def test_has(self) -> None:
        a = CacheAdapter()

        a.get = Mock(return_value=True)  # type: ignore [assignment]
        self.assertTrue(a.has('key'))

        a.get.side_effect = KeyError
        self.assertFalse(a.has('key'))

    def test_put_many(self) -> None:
        a = CacheAdapter()

        a.put = Mock()  # type: ignore [assignment]
        a.put_many({'k1': 1, 'k2': 2}, 10)

        self.assertListEqual(a.put.call_args_list,
                             [call('k1', 1, 10), call('k2', 2, 10)])

    def test_get_many(self) -> None:
        a = CacheAdapter()

        a.get = Mock()  # type: ignore [assignment]
        a.get_many(['k1', 'k2'])

        self.assertListEqual(a.get.call_args_list, [call('k1'), call('k2')])

    def test_loads(self) -> None:
        a = CacheAdapter()

        data = (1, 3.1415, False, None, {'a': 1}, (7, 8, 9), {10, 20})

        self.assertEqual(a._loads(a._dumps(data)), data)

    def test_map_key(self) -> None:
        a = CacheAdapter()
        self.assertEqual(a._map_key('pluca is great'),
                         'ecea4f8d629a85bd4e156e558fc2c9a12012e672')

    def test_map_key_composite(self) -> None:
        a = CacheAdapter()
        self.assertEqual(a._map_key(('test', 1, False, None, 3.1415)),
                         '9017e9563eafdc3b2b6232a2cb496bd79329187f')

    def test_map_key_check_type(self) -> None:
        a = CacheAdapter()
        self.assertNotEqual(a._map_key(1), a._map_key('1'))

        s1 = 'foo'
        s2 = _AlternateString('foo')

        self.assertNotEqual(a._map_key(s1), a._map_key(s2))
