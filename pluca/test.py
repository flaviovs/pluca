import abc
import uuid
import time
import unittest
from typing import TYPE_CHECKING

import pluca

if TYPE_CHECKING:
    _BaseClass = unittest.TestCase
else:
    _BaseClass = object


class CacheTester(abc.ABC, _BaseClass):

    @abc.abstractmethod
    def get_cache(self) -> pluca.Cache:
        pass

    def test_create(self) -> None:
        self.get_cache()

    def test_put_get(self) -> None:
        c = self.get_cache()
        key1 = uuid.uuid4()
        value1 = uuid.uuid4()
        key2 = uuid.uuid4()
        value2 = uuid.uuid4()
        c.put(key1, value1)
        c.put(key2, value2)
        self.assertEqual(c.get(key1), value1)
        self.assertEqual(c.get(key2), value2)

    def test_put_get_check_key_types(self) -> None:
        c = self.get_cache()
        value1 = uuid.uuid4()
        value2 = uuid.uuid4()

        c.put(1, value1)
        c.put('1', value2)

        self.assertEqual(c.get(1), value1)
        self.assertEqual(c.get('1'), value2)

    def test_get_default(self) -> None:
        c = self.get_cache()
        self.assertEqual(c.get('nonexistent', 'default'), 'default')

    def test_put_max_age(self) -> None:
        c = self.get_cache()
        key = uuid.uuid4()
        value = uuid.uuid4()
        c.put(key, value, 1)  # Expires in 1 second.
        time.sleep(1)
        with self.assertRaises(KeyError):
            c.get(key)

    def test_put_tuple_key(self) -> None:
        c = self.get_cache()
        key = (uuid.uuid4(), uuid.uuid4())
        value = uuid.uuid4()
        c.put(key, value)
        self.assertEqual(c.get(key), value)

    def test_put_list_key(self) -> None:
        c = self.get_cache()
        key = [uuid.uuid4(), uuid.uuid4()]
        value = uuid.uuid4()
        c.put(key, value)
        self.assertEqual(c.get(key), value)

    def test_put_dict_key(self) -> None:
        c = self.get_cache()
        key = {uuid.uuid4(): uuid.uuid4()}
        value = uuid.uuid4()
        c.put(key, value)
        self.assertEqual(c.get(key), value)

    def test_remove(self) -> None:
        c = self.get_cache()
        key = uuid.uuid4()
        c.put(key, 'value')
        c.remove(key)
        with self.assertRaises(KeyError):
            c.get(key)

    def test_remove_nonexistent(self) -> None:
        c = self.get_cache()
        with self.assertRaises(KeyError):
            c.remove('nonexistent')

    def test_flush(self) -> None:
        c = self.get_cache()
        key1 = uuid.uuid4()
        key2 = uuid.uuid4()
        c.put(key1, 'value1')
        c.put(key2, 'value2')
        c.flush()
        with self.assertRaises(KeyError):
            c.get(key1)
        with self.assertRaises(KeyError):
            c.get(key2)

    def test_has(self) -> None:
        c = self.get_cache()
        key = uuid.uuid4()
        value = uuid.uuid4()
        c.put(key, value)
        self.assertTrue(c.has(key))
        self.assertFalse(c.has('nonexistentkey'))

    def test_put_many(self) -> None:
        c = self.get_cache()
        key1 = uuid.uuid4()
        value1 = uuid.uuid4()
        key2 = uuid.uuid4()
        value2 = uuid.uuid4()
        c.put_many({key1: value1, key2: value2})
        self.assertEqual(c.get(key1), value1)
        self.assertEqual(c.get(key2), value2)

    def test_get_many(self) -> None:
        c = self.get_cache()
        key1 = uuid.uuid4()
        value1 = uuid.uuid4()
        key2 = uuid.uuid4()
        value2 = uuid.uuid4()
        c.put(key1, value1)
        c.put(key2, value2)
        res = dict(c.get_many([key1, key2, 'nonexistent']))
        self.assertIn(key1, res)
        self.assertEqual(res[key1], value1)
        self.assertIn(key2, res)
        self.assertEqual(res[key2], value2)
        self.assertNotIn('nonexistent', res)

    def test_get_many_default(self) -> None:
        c = self.get_cache()
        key = uuid.uuid4()
        value = uuid.uuid4()
        c.put(key, value)
        res = dict(c.get_many([key, 'nonexistent'], 'default'))

        self.assertIn(key, res)
        self.assertEqual(res[key], value)
        self.assertIn('nonexistent', res)
        self.assertEqual(res['nonexistent'], 'default')
