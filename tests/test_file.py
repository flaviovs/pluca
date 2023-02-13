import os
import unittest
import tempfile
import shutil
import uuid
import time
from pathlib import Path
from typing import Optional

import pluca
from pluca.file import create
from pluca.test import CacheTester


class TestFile(CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        self._dir: Optional[Path] = Path(
            tempfile.mkdtemp(prefix='pluca-file-test'))

    def tearDown(self) -> None:
        if self._dir is not None:
            shutil.rmtree(self._dir)
            self._dir = None

    def get_cache(self) -> pluca.Cache:
        return create(name='test', cache_dir=self._dir)

    def test_flush_empties_dir(self) -> None:
        cache = self.get_cache()
        key1 = uuid.uuid4()
        key2 = uuid.uuid4()
        cache.put(key1, 'value1')
        cache.put(key2, 'value2')
        cache.flush()
        self.assertEqual(len(os.listdir(self._dir)), 1)

    def _count_files(self, path: Optional[Path]) -> int:
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
