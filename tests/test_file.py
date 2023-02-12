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
        return create(name='test', path=self._dir)

    def test_flush_empties_dir(self) -> None:
        c = self.get_cache()
        key1 = uuid.uuid4()
        key2 = uuid.uuid4()
        c.put(key1, 'value1')
        c.put(key2, 'value2')
        c.flush()
        self.assertEqual(len([_ for _ in os.listdir(c.adapter.path)]), 0)

    def _count_files(self, path: Path) -> int:
        nr = 0
        for p in path.iterdir():
            if p.is_dir():
                nr += self._count_files(path / p)
            else:
                nr += 1
        return nr

    def test_gc(self) -> None:
        c = self.get_cache()
        key1 = uuid.uuid4()
        key2 = uuid.uuid4()
        c.put(key1, 'value1')
        c.put(key2, 'value2', 1)  # NB: expires in 1 second.
        time.sleep(1)
        c.gc()
        self.assertEqual(self._count_files(c.adapter.path), 1)
