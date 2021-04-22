import warnings
import os
import time
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

import pluca

_FILE_MAX_AGE = 1_000_000_000


@dataclass
class Cache(pluca.Cache):
    path: Optional[Path] = None
    name: Optional[str] = None
    max_age: Optional[float] = None

    def __post_init__(self):
        if self.path:
            if isinstance(self.path, str):
                self.path = Path(self.path)
            if not self.path.exists():
                raise ValueError(f'Directory does not exist: {self.path}')
            if not self.path.is_dir():
                raise ValueError(f'Not a directory: {self.path}')
        else:
            try:
                import appdirs
                self.path = Path(appdirs.user_cache_dir())
            except ModuleNotFoundError:
                self.path = Path.home() / '.cache'

        if not self.name:
            suffix = self._get_key_hash((__file__,
                                         os.stat(__file__).st_ctime))
            self.name = f'pluca-{suffix}'

        self.path /= self.name

    def _get_filename(self, khash: str) -> Path:
        assert self.path is not None
        return self.path / khash[0:2] / f'{khash[2:]}.dat'

    def _get_key_filename(self, key: Any) -> Path:
        return self._get_filename(self._get_key_hash(key))

    def _write(self, filename: Path, pickled: Any):
        with open(filename, 'wb') as fd:
            fd.write(pickled)

    def _touch_filename(self, filename: Path,
                        max_age: Optional[float] = None):
        if max_age is None:
            max_age = (self.max_age
                       if self.max_age is not None else _FILE_MAX_AGE)
        now = time.time()
        os.utime(filename, times=(now, now + max_age))

    def _touch(self, key: Any) -> None:
        filename = self._get_fresh_key_filename(key)
        if filename:
            self._touch_filename(filename)

    def _put(self, key: Any, value: Any, max_age: Optional[float] = None):
        assert self._pickle is not None
        pickled = self._pickle.dumps(value)
        filename = self._get_key_filename(key)
        try:
            self._write(filename, pickled)
        except FileNotFoundError:
            filename.parent.mkdir(parents=True)
            self._write(filename, pickled)
        self._touch_filename(filename, max_age)

    def _get(self, key: Any) -> Any:
        filename = self._get_fresh_key_filename(key)
        if not filename:
            raise KeyError(key)
        with open(filename, 'rb') as fd:
            assert self._pickle is not None
            return self._pickle.load(fd)

    def _flush(self) -> None:
        assert self.path is not None
        for path in self.path.iterdir():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                warnings.warn(f'Unexpected file in cache directory: {path}')

    def _get_fresh_key_filename(self, key: Any) -> Optional[Path]:
        filename = self._get_key_filename(key)
        return self._get_fresh_filename(filename)

    def _get_fresh_filename(self, filename: Path) -> Optional[Path]:
        try:
            mtime = filename.stat().st_mtime
        except FileNotFoundError:
            return None

        if mtime < time.time():
            filename.unlink()
            return None

        return filename

    def has(self, key: Any) -> bool:
        return self._get_fresh_key_filename(key) is not None

    def gc(self) -> None:
        assert self.path is not None
        self._gc_dir(self.path)

    def _gc_dir(self, path: Path) -> None:
        for p in path.iterdir():
            if p.is_dir():
                self._gc_dir(path / p)
            else:
                self._get_fresh_filename(path / p)
