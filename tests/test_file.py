import os
import unittest
import tempfile
import shutil
import uuid
import time
from pathlib import Path

import pluca
import pluca.file
from pluca.test import CacheTester


class TestFile(CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        self._dir: Path | None = Path(
            tempfile.mkdtemp(prefix='pluca-file-test'))

    def tearDown(self) -> None:
        if self._dir is not None:
            shutil.rmtree(self._dir)
            self._dir = None

    def get_cache(self) -> pluca.Cache:
        return pluca.file.Cache(name='test', cache_dir=self._dir)

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
                    pluca.file.Cache(name=name, cache_dir=self._dir)

    def test_name_path_traversal_rejected(self) -> None:
        assert self._dir is not None
        cache_dir = self._dir / 'cache'
        cache_dir.mkdir()
        escaped = self._dir / 'escaped'

        with self.assertRaises(ValueError):
            pluca.file.Cache(name='../escaped', cache_dir=cache_dir)

        self.assertFalse(escaped.exists())

    def test_valid_custom_name_works(self) -> None:
        assert self._dir is not None
        cache = pluca.file.Cache(name='mycache', cache_dir=self._dir)
        cache.put('key', 'value')
        self.assertEqual(cache.get('key'), 'value')

    def test_name_with_double_dot_inside_segment_works(self) -> None:
        assert self._dir is not None
        cache = pluca.file.Cache(name='part1..part2', cache_dir=self._dir)
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
