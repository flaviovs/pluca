import os
import unittest
import tempfile
import shutil
import uuid
import time
from pathlib import Path

import pluca
import pluca.file
from pluca.test import AdapterTester


class TestFile(AdapterTester, unittest.TestCase):

    def setUp(self) -> None:
        self._dir: Path | None = Path(
            tempfile.mkdtemp(prefix='pluca-file-test'))

    def tearDown(self) -> None:
        if self._dir is not None:
            shutil.rmtree(self._dir)
            self._dir = None

    def get_adapter(self) -> pluca.file.Adapter:
        return pluca.file.Adapter(name='test', cache_dir=self._dir)

    def test_invalid_name_raises_valueerror(self) -> None:
        assert self._dir is not None
        invalid_names = (
            '../escaped',
            '/tmp/pluca',
            'dir/name',
            'dir\\name',
            '..',
            '',
        )
        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    pluca.file.Adapter(name=name, cache_dir=self._dir)

    def test_name_path_traversal_rejected(self) -> None:
        assert self._dir is not None
        cache_dir = self._dir / 'cache'
        cache_dir.mkdir()
        escaped = self._dir / 'escaped'

        with self.assertRaises(ValueError):
            pluca.file.Adapter(name='../escaped', cache_dir=cache_dir)

        self.assertFalse(escaped.exists())

    def test_valid_custom_name_works(self) -> None:
        assert self._dir is not None
        cache = pluca.Cache(pluca.file.Adapter(name='mycache',
                                               cache_dir=self._dir))
        cache.put('key', 'value')
        self.assertEqual(cache.get('key'), 'value')

    def test_locking_none_works(self) -> None:
        assert self._dir is not None
        cache = pluca.Cache(pluca.file.Adapter(
            name='nolock',
            cache_dir=self._dir,
            locking=None,
        ))
        cache.put('key', 'value')
        self.assertEqual(cache.get('key'), 'value')
        self.assertIsNone(cache.locking)

    def test_locking_mkdir_works(self) -> None:
        assert self._dir is not None
        cache = pluca.Cache(pluca.file.Adapter(
            name='mkdirlock',
            cache_dir=self._dir,
            locking='mkdir',
        ))
        cache.put('key', 'value')
        self.assertEqual(cache.get('key'), 'value')
        self.assertEqual(cache.locking, 'mkdir')

    def test_locking_mkdir_defaults(self) -> None:
        assert self._dir is not None
        cache = pluca.Cache(pluca.file.Adapter(
            name='mkdirdefaults',
            cache_dir=self._dir,
            locking='mkdir',
        ))
        self.assertEqual(cache.mkdir_stale_age, 300.0)
        self.assertEqual(cache.mkdir_wait_timeout, 30.0)
        self.assertEqual(cache.mkdir_poll_interval, 0.05)

    def test_locking_mkdir_option_validation(self) -> None:
        assert self._dir is not None

        with self.assertRaises(ValueError):
            pluca.file.Adapter(name='bad1', cache_dir=self._dir,
                               locking='mkdir', mkdir_stale_age=0)
        with self.assertRaises(ValueError):
            pluca.file.Adapter(name='bad2', cache_dir=self._dir,
                               locking='mkdir', mkdir_wait_timeout=0)
        with self.assertRaises(ValueError):
            pluca.file.Adapter(name='bad3', cache_dir=self._dir,
                               locking='mkdir', mkdir_poll_interval=0)

    def test_locking_mkdir_owner_file_format(self) -> None:
        assert self._dir is not None
        cache = pluca.Cache(pluca.file.Adapter(name='mkdirowner',
                                               cache_dir=self._dir,
                                               locking='mkdir'))
        filename = cache._get_filename(cache._map_key('k'))
        with cache._lock_entry_mkdir(filename, create=True):
            owner_file = Path(f'{filename}.lock') / 'owner'
            self.assertTrue(owner_file.exists())
            data = owner_file.read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(data), 3)
            self.assertEqual(int(data[0]), os.getpid())
            self.assertTrue(data[1])
            self.assertGreater(float(data[2]), 0.0)

    def test_locking_mkdir_stale_reclaim(self) -> None:
        assert self._dir is not None
        cache = pluca.Cache(pluca.file.Adapter(name='mkdirstale',
                                               cache_dir=self._dir,
                                               locking='mkdir',
                                               mkdir_stale_age=0.01,
                                               mkdir_wait_timeout=1,
                                               mkdir_poll_interval=0.01))
        filename = cache._get_filename(cache._map_key('k'))
        filename.parent.mkdir(parents=True)
        lock_dir = Path(f'{filename}.lock')
        lock_dir.mkdir()
        owner_file = lock_dir / 'owner'
        owner_file.write_text('999999\nother-host\n0\n', encoding='utf-8')

        cache.put('k', 'v')
        self.assertEqual(cache.get('k'), 'v')
        self.assertFalse(lock_dir.exists())

    def test_locking_mkdir_wait_timeout(self) -> None:
        assert self._dir is not None
        cache = pluca.Cache(pluca.file.Adapter(name='mkdirtimeout',
                                               cache_dir=self._dir,
                                               locking='mkdir',
                                               mkdir_stale_age=300,
                                               mkdir_wait_timeout=0.05,
                                               mkdir_poll_interval=0.01))
        filename = cache._get_filename(cache._map_key('k'))
        filename.parent.mkdir(parents=True)
        lock_dir = Path(f'{filename}.lock')
        lock_dir.mkdir()
        owner_file = lock_dir / 'owner'
        owner_file.write_text(f'{os.getpid()}\nlocal\n{time.time()}\n',
                              encoding='utf-8')

        with self.assertRaises(TimeoutError):
            cache.put('k', 'v')

    def test_locking_auto_works(self) -> None:
        assert self._dir is not None
        cache = pluca.Cache(pluca.file.Adapter(
            name='autolock',
            cache_dir=self._dir,
            locking='auto',
        ))
        cache.put('key', 'value')
        self.assertEqual(cache.get('key'), 'value')

        if os.name == 'nt':
            self.assertEqual(cache.locking, 'msvcrt')
        else:
            self.assertEqual(cache.locking, 'flock')

    def test_invalid_locking_raises_valueerror(self) -> None:
        assert self._dir is not None

        with self.assertRaises(ValueError):
            pluca.file.Adapter(name='invalid', cache_dir=self._dir,
                               locking='invalid')

    def test_unsupported_locking_raises_valueerror(self) -> None:
        assert self._dir is not None

        locking = 'flock' if os.name == 'nt' else 'msvcrt'
        with self.assertRaises(ValueError):
            pluca.file.Adapter(name='unsupported', cache_dir=self._dir,
                               locking=locking)

    def test_name_with_double_dot_inside_segment_works(self) -> None:
        assert self._dir is not None
        cache = pluca.Cache(pluca.file.Adapter(name='part1..part2',
                                               cache_dir=self._dir))
        cache.put('key', 'value')
        self.assertEqual(cache.get('key'), 'value')

    def test_flush_empties_dir(self) -> None:
        cache = self.get_cache()
        key1 = uuid.uuid4()
        key2 = uuid.uuid4()
        cache.put(key1, 'value1')
        cache.put(key2, 'value2')
        cache.flush()
        self.assertEqual(len(os.listdir(self._dir)), 1)

    def test_flush_on_fresh_cache_is_noop(self) -> None:
        cache = self.get_cache()
        cache.flush()
        self.assertEqual(len(os.listdir(self._dir)), 0)

    def _count_files(self, path: Path | None) -> int:
        assert path is not None

        nr = 0
        for entry in path.iterdir():
            if entry.is_dir():
                nr += self._count_files(path / entry)
            else:
                nr += 1
        return nr

    def test_gc(self) -> None:
        cache = self.get_cache()
        key1 = uuid.uuid4()
        key2 = uuid.uuid4()
        cache.put(key1, 'value1')
        cache.put(key2, 'value2', 1)  # NB: expires in 1 second.
        time.sleep(1)
        cache.gc()
        self.assertEqual(self._count_files(self._dir), 1)

    def test_gc_on_fresh_cache_is_noop(self) -> None:
        cache = self.get_cache()
        cache.gc()
        self.assertEqual(len(os.listdir(self._dir)), 0)

    def test_gc_after_manual_cache_root_removal_is_noop(self) -> None:
        assert self._dir is not None
        cache = self.get_cache()
        cache.put('foo', 'bar')
        shutil.rmtree(self._dir / 'test')
        cache.gc()
        self.assertEqual(len(os.listdir(self._dir)), 0)
