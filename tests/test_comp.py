import time
import tempfile
import unittest
from typing import Any

import pluca
import pluca.comp
import pluca.memory
import pluca.null
from pluca.test import CacheTester


class TestComposite(CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        # pylint: disable-next=consider-using-with
        self._tempdir = tempfile.TemporaryDirectory()

        self._cache1 = pluca.memory.Cache()
        self._cache2 = pluca.memory.Cache()
        self._cache3 = pluca.memory.Cache()

    def tearDown(self) -> None:
        self._tempdir.cleanup()

    def get_cache(self) -> pluca.comp.Cache:
        cache = pluca.comp.Cache()

        cache.add_cache(self._cache1)
        cache.add_cache(self._cache2)
        cache.add_cache(self._cache3)

        return cache

    def test_caches_property(self) -> None:
        cache = self.get_cache()

        self.assertEqual(cache.caches,
                         [self._cache1, self._cache2, self._cache3])

    def test_add_cache_config(self) -> None:
        cache = pluca.comp.Cache()

        cache.add_cache_config({
            'class': 'pluca.memory.Cache',
            'max_entries': 10,
        })

        cache.add_cache_config({
            'class': 'pluca.null.Cache',
        })

        cache1: pluca.memory.Cache
        cache2: pluca.null.Cache
        cache1, cache2 = cache.caches  # type: ignore [assignment]

        self.assertIsInstance(cache1, pluca.memory.Cache)
        self.assertEqual(cache1.max_entries, 10)

        self.assertIsInstance(cache2, pluca.null.Cache)

    def test_constructor(self) -> None:
        cache = pluca.comp.Cache([
            {'class': 'pluca.memory.Cache', 'max_entries': 10},
            {'class': 'pluca.null.Cache'},
        ])

        cache1: pluca.memory.Cache
        cache2: pluca.null.Cache
        cache1, cache2 = cache.caches  # type: ignore [assignment]

        self.assertIsInstance(cache1, pluca.memory.Cache)
        self.assertEqual(cache1.max_entries, 10)

        self.assertIsInstance(cache2, pluca.null.Cache)

    def test_comp_put(self) -> None:
        cache = self.get_cache()

        cache.put('foo', 'bar')

        self.assertTrue(self._cache1.has('foo'))
        self.assertTrue(self._cache2.has('foo'))
        self.assertTrue(self._cache3.has('foo'))

    def test_comp_get(self) -> None:
        cache = self.get_cache()

        self._cache3.put('foo', 'bar')

        self.assertEqual(cache.get('foo'), 'bar')

    def test_get_order(self) -> None:
        cache = self.get_cache()

        self._cache1.put('foo', 'bar1')
        self._cache2.put('foo', 'bar2')
        self._cache3.put('foo', 'bar3')

        self.assertEqual(cache.get('foo'), 'bar1')

    def test_comp_gc(self) -> None:
        cache = self.get_cache()

        self._cache1.put('expired1', 'bar', max_age=0.1)
        self._cache2.put('expired2', 'bar', max_age=0.1)
        self._cache3.put('expired3', 'bar', max_age=0.1)

        time.sleep(0.1)

        cache.gc()

        self.assertFalse(self._cache1.has('expired1'))
        self.assertFalse(self._cache2.has('expired2'))
        self.assertFalse(self._cache3.has('expired3'))

    def test_comp_get_put(self) -> None:
        cache = self.get_cache()

        call = 0

        def func() -> Any:
            nonlocal call
            call += 1
            return f'bar{call}'

        cache.get_put('foo', func)

        self.assertEqual(call, 1)

        self.assertEqual(self._cache1.get('foo'), 'bar1')
        self.assertEqual(self._cache2.get('foo'), 'bar1')
        self.assertEqual(self._cache3.get('foo'), 'bar1')

    def test_comp_remove(self) -> None:
        cache = self.get_cache()

        self._cache1.put('foo', 'bar')
        self._cache2.put('foo', 'bar')
        self._cache3.put('foo', 'bar')

        cache.remove('foo')

        self.assertFalse(self._cache1.has('foo'))
        self.assertFalse(self._cache2.has('foo'))
        self.assertFalse(self._cache3.has('foo'))

    def test_comp_remove_all(self) -> None:
        cache = self.get_cache()

        entries = {'gone1': 'bar', 'stay': 'goo', 'gone2': 'moo'}

        for key, value in entries.items():
            self._cache1.put(key, value)
            self._cache2.put(key, value)
            self._cache3.put(key, value)

        cache.remove_many(['gone1', 'gone2'])

        self.assertFalse(self._cache1.has('gone1'))
        self.assertTrue(self._cache1.has('stay'))
        self.assertFalse(self._cache1.has('gone2'))

        self.assertFalse(self._cache2.has('gone1'))
        self.assertTrue(self._cache2.has('stay'))
        self.assertFalse(self._cache2.has('gone2'))

        self.assertFalse(self._cache3.has('gone1'))
        self.assertTrue(self._cache3.has('stay'))
        self.assertFalse(self._cache3.has('gone2'))

    def test_comp_flush(self) -> None:
        cache = self.get_cache()

        self._cache1.put('foo', 'bar')
        self._cache2.put('foo', 'bar')
        self._cache3.put('foo', 'bar')

        cache.flush()

        self.assertFalse(self._cache1.has('foo'))
        self.assertFalse(self._cache2.has('foo'))
        self.assertFalse(self._cache3.has('foo'))

    def test_has(self) -> None:
        cache = self.get_cache()

        self._cache3.put('foo', 'bar')

        self.assertTrue(cache.has('foo'))
        self.assertFalse(cache.has('not-there'))
