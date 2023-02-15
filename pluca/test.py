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


# Yes, I know this is big, but in this case bigger is better, therefore
# pylint: disable-next=too-many-public-methods
class CacheTester(abc.ABC, _BaseClass):

    @abc.abstractmethod
    def get_cache(self) -> pluca.Cache:
        pass

    def test_create(self) -> None:
        self.get_cache()

    def test_put_get(self) -> None:
        cache = self.get_cache()
        key1 = uuid.uuid4()
        value1 = uuid.uuid4()
        key2 = uuid.uuid4()
        value2 = uuid.uuid4()
        cache.put(key1, value1)
        cache.put(key2, value2)
        self.assertEqual(cache.get(key1), value1)
        self.assertEqual(cache.get(key2), value2)

    def test_put_get_check_key_types(self) -> None:
        cache = self.get_cache()
        value1 = uuid.uuid4()
        value2 = uuid.uuid4()

        cache.put(1, value1)
        cache.put('1', value2)

        self.assertEqual(cache.get(1), value1)
        self.assertEqual(cache.get('1'), value2)

    def test_get_default(self) -> None:
        cache = self.get_cache()
        self.assertEqual(cache.get('nonexistent', 'default'), 'default')

    def test_get_default_none(self) -> None:
        cache = self.get_cache()
        self.assertIsNone(cache.get('nonexistent', None))

    def test_put_max_age(self) -> None:
        cache = self.get_cache()
        key = uuid.uuid4()
        value = uuid.uuid4()
        cache.put(key, value, 1)  # Expires in 1 second.
        time.sleep(1)
        with self.assertRaises(KeyError) as ctx:
            cache.get(key)
        self.assertEqual(ctx.exception.args, (key,))

    def test_put_max_age_validate(self) -> None:
        cache = self.get_cache()
        with self.assertRaises(ValueError):
            cache.put('k', 'v', -1)

    def test_put_tuple_key(self) -> None:
        cache = self.get_cache()
        key = (uuid.uuid4(), uuid.uuid4())
        value = uuid.uuid4()
        cache.put(key, value)
        self.assertEqual(cache.get(key), value)

    def test_put_list_key(self) -> None:
        cache = self.get_cache()
        key = [uuid.uuid4(), uuid.uuid4()]
        value = uuid.uuid4()
        cache.put(key, value)
        self.assertEqual(cache.get(key), value)

    def test_put_dict_key(self) -> None:
        cache = self.get_cache()
        key = {uuid.uuid4(): uuid.uuid4()}
        value = uuid.uuid4()
        cache.put(key, value)
        self.assertEqual(cache.get(key), value)

    def test_remove(self) -> None:
        cache = self.get_cache()
        key = uuid.uuid4()
        cache.put(key, 'value')
        cache.remove(key)
        with self.assertRaises(KeyError):
            cache.get(key)

    def test_remove_nonexistent(self) -> None:
        cache = self.get_cache()
        with self.assertRaises(KeyError) as ctx:
            cache.remove('nonexistent')
        self.assertEqual(ctx.exception.args, ('nonexistent',))

    def test_flush(self) -> None:
        cache = self.get_cache()
        key1 = uuid.uuid4()
        key2 = uuid.uuid4()
        cache.put(key1, 'value1')
        cache.put(key2, 'value2')
        cache.flush()
        with self.assertRaises(KeyError):
            cache.get(key1)
        with self.assertRaises(KeyError):
            cache.get(key2)

    def test_has(self) -> None:
        cache = self.get_cache()
        key = uuid.uuid4()
        value = uuid.uuid4()
        cache.put(key, value)
        self.assertTrue(cache.has(key))
        self.assertFalse(cache.has('nonexistentkey'))

    def test_put_many(self) -> None:
        cache = self.get_cache()
        key1 = uuid.uuid4()
        value1 = uuid.uuid4()
        key2 = uuid.uuid4()
        value2 = uuid.uuid4()
        cache.put_many({key1: value1, key2: value2})
        self.assertEqual(cache.get(key1), value1)
        self.assertEqual(cache.get(key2), value2)

    def test_get_many(self) -> None:
        cache = self.get_cache()
        key1 = uuid.uuid4()
        value1 = uuid.uuid4()
        key2 = uuid.uuid4()
        value2 = uuid.uuid4()
        cache.put(key1, value1)
        cache.put(key2, value2)
        res = dict(cache.get_many([key1, key2, 'nonexistent']))
        self.assertIn(key1, res)
        self.assertEqual(res[key1], value1)
        self.assertIn(key2, res)
        self.assertEqual(res[key2], value2)
        self.assertNotIn('nonexistent', res)

    def test_get_many_default(self) -> None:
        cache = self.get_cache()
        key = uuid.uuid4()
        value = uuid.uuid4()
        cache.put(key, value)
        res = dict(cache.get_many([key, 'nonexistent'], 'default'))

        self.assertIn(key, res)
        self.assertEqual(res[key], value)
        self.assertIn('nonexistent', res)
        self.assertEqual(res['nonexistent'], 'default')

    def test_get_many_default_none(self) -> None:
        cache = self.get_cache()
        key = uuid.uuid4()
        value = uuid.uuid4()
        cache.put(key, value)
        res = dict(cache.get_many([key, 'nonexistent'], None))

        self.assertIn(key, res)
        self.assertEqual(res[key], value)
        self.assertIn('nonexistent', res)
        self.assertIsNone(res['nonexistent'])

    def test_decorator(self) -> None:
        cache = self.get_cache()

        calls = 0

        @cache
        def func(val1: int, val2: int) -> int:
            nonlocal calls
            calls += 1
            return val1 + val2

        self.assertEqual(func(1, 2), 3)
        self.assertEqual(func(3, 4), 7)
        self.assertEqual(func(1, 2), 3)

        self.assertEqual(calls, 2)

    def test_gc(self) -> None:
        # This really only checks that the method is not generating
        # any errors.
        self.get_cache().gc()
