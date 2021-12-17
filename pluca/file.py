import warnings
import os
import time
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, BinaryIO

import pluca

_FILE_MAX_AGE = 1_000_000_000

_DIR_PREFIX = 'cache-'


@dataclass
class CacheAdapter(pluca.CacheAdapter):
    path: Optional[Path] = None
    name: Optional[str] = None

    def __post_init__(self):
        if self.path:
            if isinstance(self.path, str):
                self.path = Path(self.path)
            if not self.path.exists():
                raise pluca.CacheError('Directory does not exist: '
                                       f'{self.path}')
            if not self.path.is_dir():
                raise pluca.CacheError(f'Not a directory: {self.path}')
        else:
            try:
                import appdirs
                self.path = Path(appdirs.user_cache_dir())
            except ModuleNotFoundError:
                self.path = Path.home() / '.cache'

        if not self.name:
            suffix = self._get_cache_key((__file__,
                                          os.stat(__file__).st_ctime))
            self.name = f'pluca-{suffix}'

        self.path /= self.name

    def _dump(self, obj: Any, fd: BinaryIO) -> None:
        import pickle
        pickle.dump(fd, obj)

    def _load(self, fd: BinaryIO) -> Any:
        import pickle
        return pickle.load(fd)

    def _get_filename(self, khash: str) -> Path:
        assert self.path is not None
        return self.path / f'{_DIR_PREFIX}{khash[0:2]}' / f'{khash[2:]}.dat'

    def _get_key_filename(self, key: Any) -> Path:
        return self._get_filename(self._get_cache_key(key))

    def _write(self, filename: Path, data: bytes):
        with open(filename, 'wb') as fd:
            fd.write(data)

    def _set_max_age(self, filename: Path,
                     max_age: Optional[float] = None):
        if max_age is None:
            max_age = _FILE_MAX_AGE
        now = time.time()
        os.utime(filename, times=(now, now + max_age))

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

    def put(self, key: Any, value: Any, max_age: Optional[float] = None):
        data = self._dumps(value)
        filename = self._get_key_filename(key)
        try:
            self._write(filename, data)
        except FileNotFoundError:
            filename.parent.mkdir(parents=True)
            self._write(filename, data)
        self._set_max_age(filename, max_age)

    def get(self, key: Any) -> Any:
        filename = self._get_fresh_key_filename(key)
        if not filename:
            raise KeyError(key)
        with open(filename, 'rb') as fd:
            return self._load(fd)

    def remove(self, key: Any) -> None:
        try:
            self._get_key_filename(key).unlink()
        except FileNotFoundError as ex:
            raise KeyError(key) from ex

    def flush(self) -> None:
        assert self.path is not None
        for path in self.path.iterdir():
            if path.name.startswith(_DIR_PREFIX) and path.is_dir():
                shutil.rmtree(path)
            else:
                warnings.warn(f'Unexpected entry in cache directory: {path}')

    def has(self, key: Any) -> bool:
        return self._get_fresh_key_filename(key) is not None

    def _gc_dir(self, path: Path) -> None:
        for p in path.iterdir():
            if p.is_dir():
                self._gc_dir(path / p)
            else:
                self._get_fresh_filename(path / p)

    def gc(self) -> None:
        assert self.path is not None
        self._gc_dir(self.path)


def create(path: Optional[Path] = None,
           name: Optional[str] = None):
    return pluca.Cache(CacheAdapter(path=path, name=name))
