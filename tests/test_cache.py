import sys
import unittest
import tempfile
import time
from typing import Any

import pluca.file
import pluca.null
import pluca.memory
import pluca.cache as plc


class _ConfigProbeAdapter:

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def put_mapped(self, mkey: Any, value: Any,
                   max_age: float | None = None) -> None:
        _ = (mkey, value, max_age)

    def get_mapped(self, mkey: Any) -> Any:
        raise KeyError(mkey)

    def remove_mapped(self, mkey: Any) -> None:
        raise KeyError(mkey)

    def flush(self) -> None:
        pass

    def has_mapped(self, mkey: Any) -> bool:
        _ = mkey
        return False

    def put_many_mapped(self,
                        data: Any,
                        max_age: float | None = None) -> None:
        raise NotImplementedError

    def get_many_mapped(self, keys: Any,
                        default: Any = ...) -> list[tuple[Any, Any]]:
        raise NotImplementedError

    def remove_many_mapped(self, keys: Any) -> None:
        raise NotImplementedError

    def gc(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


# pylint: disable=too-many-public-methods
class TestCache(unittest.TestCase):

    def _assert_file_cache(self, cache: pluca.Cache) -> None:
        self.assertIsInstance(cache.adapter, pluca.file.FileAdapter)

    def _assert_memory_cache(self, cache: pluca.Cache) -> None:
        self.assertIsInstance(cache.adapter, pluca.memory.MemoryAdapter)

    def _assert_null_cache(self, cache: pluca.Cache) -> None:
        self.assertIsInstance(cache.adapter, pluca.null.NullAdapter)

    def setUp(self) -> None:
        plc.remove_all()
        # Make sure that pluca module used in the tests are unloaded
        # before tests.
        for mod in ('pluca.file', 'pluca.memory', 'pluca.null'):
            try:
                del sys.modules[mod]
            except KeyError:
                pass

    def test_add_get(self) -> None:
        plc.add(None, 'pluca.file')
        plc.add('mod', 'pluca.null')
        plc.add('pkg.mod', 'pluca.memory')

        cache = plc.get_cache()
        self._assert_file_cache(cache)

        cache = plc.get_cache('non-existent')
        self._assert_file_cache(cache)

        cache = plc.get_cache('mod')
        self._assert_null_cache(cache)

        cache = plc.get_cache('pkg.mod')
        self._assert_memory_cache(cache)

    def test_add_get_child(self) -> None:
        plc.add(None, 'pluca.file')
        plc.add('pkg', 'pluca.memory')
        plc.add('pkg.mod', 'pluca.null')
        cache = plc.get_child('pkg', 'mod')
        self._assert_null_cache(cache)

    def test_get_child_empty_parent(self) -> None:
        plc.add(None, 'pluca.file')
        plc.add('mod', 'pluca.null')

        cache = plc.get_cache('mod')

        self.assertIs(plc.get_child(None, 'mod'), cache)
        self.assertIs(plc.get_child('', 'mod'), cache)

    def test_add_no_root(self) -> None:
        plc.add('mod', 'pluca.null')
        cache = plc.get_cache('mod')
        self._assert_null_cache(cache)
        cache = plc.get_cache('nonexistend')
        self._assert_file_cache(cache)

    def test_add_reuse(self) -> None:
        plc.add(None, 'pluca.file')
        plc.add('mod', 'pluca.file')

        root_cache = plc.get_cache()
        mod_cache = plc.get_cache('mod')
        self.assertIs(root_cache, mod_cache)

    def test_add_no_reuse(self) -> None:
        plc.add(None, 'pluca.file')
        plc.add('mod', 'pluca.file', reuse=False)

        root_cache = plc.get_cache()
        mod_cache = plc.get_cache('mod')
        self.assertIsNot(root_cache, mod_cache)

    def test_add_no_implicit_reuse(self) -> None:
        plc.add('foo', 'pluca.file', name='foo')
        plc.add('bar', 'pluca.file', name='bar')
        self.assertIsNot(plc.get_cache('foo'), plc.get_cache('bar'))

    def test_add_dup_name(self) -> None:
        plc.add('name', 'pluca.null')
        with self.assertRaises(ValueError):
            plc.add('name', 'pluca.memory')

    def test_basic_config(self) -> None:
        plc.basic_config()

        cache = plc.get_cache()
        self._assert_file_cache(cache)

    def test_add_file_locking_none(self) -> None:
        plc.add(None, 'pluca.file', locking=None)
        cache = plc.get_cache()
        self._assert_file_cache(cache)
        self.assertIsNone(cache.locking)

    def test_add_file_invalid_locking(self) -> None:
        with self.assertRaises(ValueError):
            plc.add(None, 'pluca.file', locking='invalid')

    def test_add_file_locking_mkdir(self) -> None:
        plc.add(None, 'pluca.file', locking='mkdir')
        cache = plc.get_cache()
        self._assert_file_cache(cache)
        self.assertEqual(cache.locking, 'mkdir')

    def test_add_file_locking_mkdir_options(self) -> None:
        plc.add(None, 'pluca.file', locking='mkdir',
                mkdir_stale_age=10,
                mkdir_wait_timeout=2,
                mkdir_poll_interval=0.01)
        cache = plc.get_cache()
        self._assert_file_cache(cache)
        self.assertEqual(cache.mkdir_stale_age, 10)
        self.assertEqual(cache.mkdir_wait_timeout, 2)
        self.assertEqual(cache.mkdir_poll_interval, 0.01)

    def test_basic_config_called_explicitly(self) -> None:
        cache = plc.get_cache()
        self._assert_file_cache(cache)

    def test_remove(self) -> None:
        plc.add(None, 'pluca.file')
        plc.add('mod', 'pluca.null')
        plc.remove('mod')

        cache = plc.get_cache('mod')
        self._assert_file_cache(cache)

    def test_remove_root(self) -> None:
        plc.add(None, 'pluca.file')

        plc.remove()

        cache = plc.get_cache('mod')
        self._assert_file_cache(cache)

    def test_remove_root_multiple_times(self) -> None:
        plc.remove()
        plc.remove()  # NB: should not issue KeyError

    def test_remove_raises_keyerror(self) -> None:
        with self.assertRaises(KeyError) as ctx:
            plc.remove('mod')
        self.assertEqual(ctx.exception.args, ('mod',))

    def test_remove_all(self) -> None:
        plc.add(None, 'pluca.null')
        plc.add('mod', 'pluca.null')
        plc.add('pkg.mod', 'pluca.null')

        plc.remove_all()

        self._assert_file_cache(plc.get_cache('pkg.mod'))
        self._assert_file_cache(plc.get_cache('mod'))
        self._assert_file_cache(plc.get_cache())

    def test_from_dict(self) -> None:
        plc.from_dict({
            'factory': 'pluca.file',
            'caches': {
                'mod': {
                    'factory': 'pluca.null',
                },
                'pkg.mod': {
                    'factory': 'pluca.memory',
                    'max_entries': 10,
                },
            },
        })

        cache = plc.get_cache()
        self._assert_file_cache(cache)

        cache = plc.get_cache('non-existent')
        self._assert_file_cache(cache)

        cache = plc.get_cache('mod')
        self._assert_null_cache(cache)

        cache = plc.get_cache('pkg.mod')
        self._assert_memory_cache(cache)

    def test_from_dict_allowed_class_modules(self) -> None:
        with self.assertRaises(ValueError):
            plc.from_dict({
                'factory': 'tests.test_cache:_ConfigProbeAdapter',
            }, allowed_class_modules=('pluca',))

        plc.from_dict({
            'factory': 'tests.test_cache:_ConfigProbeAdapter',
        }, allowed_class_modules=('tests',))
        self.assertEqual(plc.get_cache().kwargs, {})

    def test_reconfig_basic(self) -> None:
        plc.basic_config('pluca.file')
        plc.basic_config('pluca.null')
        cache = plc.get_cache('foo')
        self._assert_null_cache(cache)

    def test_reconfig_from_dict(self) -> None:
        plc.from_dict({'factory': 'pluca.file'})
        plc.from_dict({'factory': 'pluca.null'})
        cache = plc.get_cache('foo')
        self._assert_null_cache(cache)

    def test_module_only_class_defaults_to_cache(self) -> None:
        plc.add(None, 'pluca.memory')
        self._assert_memory_cache(plc.get_cache())

    def test_short_name_is_treated_as_module(self) -> None:
        with self.assertRaises(ModuleNotFoundError):
            plc.add(None, 'memory')

    def test_from_config(self) -> None:
        # pylint: disable-next=consider-using-with
        temp = tempfile.NamedTemporaryFile(mode='w+', suffix='.ini')
        temp.write('''
        [__root__]
        factory = pluca.file

        [mod]
        factory = pluca.null

        [pkg.mod]
        factory = pluca.memory
        max_entries = 2
        ''')
        temp.flush()
        temp.seek(0)

        plc.from_config(temp.name)

        cache = plc.get_cache()
        self._assert_file_cache(cache)

        cache = plc.get_cache('non-existent')
        self._assert_file_cache(cache)

        cache = plc.get_cache('mod')
        self._assert_null_cache(cache)

        cache = plc.get_cache('pkg.mod')
        self._assert_memory_cache(cache)
        self.assertEqual(cache.max_entries, 2)
        self.assertIsInstance(cache.max_entries, int)

        cache.put('a', 1)
        cache.put('b', 2)
        cache.put('c', 3)
        self.assertTrue(cache.has('c'))

    def test_from_config_file_locking_none(self) -> None:
        # pylint: disable-next=consider-using-with
        temp = tempfile.NamedTemporaryFile(mode='w+', suffix='.ini')
        temp.write('''
        [__root__]
        factory = pluca.file
        locking = none
        ''')
        temp.flush()
        temp.seek(0)

        plc.from_config(temp.name)
        cache = plc.get_cache()
        self._assert_file_cache(cache)
        self.assertIsNone(cache.locking)

    def test_from_config_file_locking_mkdir_options(self) -> None:
        # pylint: disable-next=consider-using-with
        temp = tempfile.NamedTemporaryFile(mode='w+', suffix='.ini')
        temp.write('''
        [__root__]
        factory = pluca.file
        locking = mkdir
        mkdir_stale_age = 10
        mkdir_wait_timeout = 2
        mkdir_poll_interval = 0.01
        ''')
        temp.flush()
        temp.seek(0)

        plc.from_config(temp.name)
        cache = plc.get_cache()
        self._assert_file_cache(cache)
        self.assertEqual(cache.locking, 'mkdir')
        self.assertEqual(cache.mkdir_stale_age, 10)
        self.assertEqual(cache.mkdir_wait_timeout, 2)
        self.assertEqual(cache.mkdir_poll_interval, 0.01)

    def test_from_config_allowed_class_modules(self) -> None:
        # pylint: disable-next=consider-using-with
        temp = tempfile.NamedTemporaryFile(mode='w+', suffix='.ini')
        temp.write('''
        [__root__]
        factory = tests.test_cache:_ConfigProbeAdapter
        ''')
        temp.flush()
        temp.seek(0)

        with self.assertRaises(ValueError):
            plc.from_config(temp.name, allowed_class_modules=('pluca',))

        plc.from_config(temp.name, allowed_class_modules=('tests',))
        self.assertEqual(plc.get_cache().kwargs, {})

    def test_add_allowed_class_modules(self) -> None:
        with self.assertRaises(ValueError):
            plc.add(None, 'tests.test_cache:_ConfigProbeAdapter',
                    allowed_class_modules=('pluca',))

        plc.add(None, 'tests.test_cache:_ConfigProbeAdapter',
                allowed_class_modules=('tests',))
        self.assertEqual(plc.get_cache().kwargs, {})

    def test_from_config_value_coercion(self) -> None:
        # pylint: disable-next=consider-using-with
        temp = tempfile.NamedTemporaryFile(mode='w+', suffix='.ini')
        temp.write('''
        [__root__]
        factory = tests.test_cache:_ConfigProbeAdapter
        enabled = true
        disabled = false
        count = 10
        threshold = 0.5
        label = cache-v1

        [mod]
        factory = tests.test_cache:_ConfigProbeAdapter
        count = 20
        enabled = false
        threshold = 2.5
        label = cache-v2
        ''')
        temp.flush()
        temp.seek(0)

        plc.from_config(temp.name)

        root = plc.get_cache()
        self.assertIs(root.kwargs['enabled'], True)
        self.assertIs(root.kwargs['disabled'], False)
        self.assertEqual(root.kwargs['count'], 10)
        self.assertEqual(root.kwargs['threshold'], 0.5)
        self.assertEqual(root.kwargs['label'], 'cache-v1')

        mod = plc.get_cache('mod')
        self.assertEqual(mod.kwargs['count'], 20)
        self.assertIs(mod.kwargs['enabled'], False)
        self.assertEqual(mod.kwargs['threshold'], 2.5)
        self.assertEqual(mod.kwargs['label'], 'cache-v2')

    def test_flush(self) -> None:
        plc.add(None, 'pluca.memory')
        plc.add('mod', 'pluca.file')

        plc.get_cache().put('foo', 'bar')
        plc.get_cache('mod').put('zee', 'lee')

        plc.flush()

        self.assertFalse(plc.get_cache().has('foo'))
        self.assertFalse(plc.get_cache('mod').has('zee'))

    def test_gc(self) -> None:
        plc.add(None, 'pluca.memory')
        plc.add('mod', 'pluca.file')

        plc.get_cache().put('foo', 'bar', max_age=1)
        plc.get_cache('mod').put('zee', 'lee', max_age=1)

        time.sleep(1)

        plc.gc()

        self.assertFalse(plc.get_cache().has('foo'))
        self.assertFalse(plc.get_cache('mod').has('zee'))
