import warnings
import os
import time
import shutil
from pathlib import Path
from typing import Any, BinaryIO

import pluca

_FILE_MAX_AGE = 1_000_000_000

_DIR_PREFIX = 'cache-'


def _validate_name(name: str) -> None:
    if not name:
        raise ValueError('Cache name must be a non-empty string')
    if os.path.isabs(name):
        raise ValueError(f'Cache name must not be absolute: {name!r}')
    if '/' in name or '\\' in name:
        raise ValueError(
            f'Cache name must not contain path separators: {name!r}')
    if name in ('.', '..'):
        raise ValueError(
            f'Cache name must not contain traversal segments: {name!r}')


def _resolve_cache_root(cache_dir: Path, name: str) -> Path:
    base = cache_dir.resolve()
    cache_root = (base / name).resolve()
    try:
        cache_root.relative_to(base)
    except ValueError as ex:
        raise ValueError(f'Invalid cache name: {name!r}') from ex
    return cache_root


class FileCache(pluca.Cache):
    """File cache for pluca.

    Store cache entries on the file system.

    Cache entries are stored by default in directories under `.cache`
    in the user home directory (as returned by
    `pathlib.Path.home()`). The location of this cache directory can
    be changed by passing a new directory path in the `path`
    parameter.

    To support multiple file caches in the same app, each cache object
    has its own directory under the cache directory. By default, these
    directories are named `pluca-XXXXX`, where _XXXXX_ is a
    semi-random string. However a custom name can be passed on the
    `name` parameter for the cache.

    Args:
        path: Optional path where to store file caches.
        name: The cache directory name.

    """

    def __init__(self, name: str = 'pluca',
                 cache_dir: Path | None = None) -> None:

        if cache_dir is None:
            try:
                import appdirs  # pylint: disable=import-outside-toplevel
                cache_dir = Path(appdirs.user_cache_dir())
            except ModuleNotFoundError:
                cache_dir = Path.home() / '.cache'
        elif not isinstance(cache_dir, Path):
            cache_dir = Path(cache_dir)

        if not cache_dir.exists():
            cache_dir.mkdir(parents=True)

        _validate_name(name)
        self._cache_root = _resolve_cache_root(cache_dir, name)

        self.name = name
        self.cache_dir = cache_dir

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}'
                f'(name={self.name!r}, cache_dir={self.cache_dir!r})')

    def _dump(self, obj: Any, fd: BinaryIO) -> None:
        import pickle  # pylint: disable=import-outside-toplevel
        pickle.dump(obj, fd)

    def _load(self, fd: BinaryIO) -> Any:
        import pickle  # pylint: disable=import-outside-toplevel
        return pickle.load(fd)

    def _get_filename(self, mkey: str) -> Path:
        return (self._cache_root
                / f'{_DIR_PREFIX}{mkey[0:2]}' / f'{mkey[2:]}.dat')

    def _write(self, filename: Path, value: Any) -> None:
        temp = filename.with_suffix('.tmp')
        while True:
            try:
                fd = open(temp, 'xb')  # pylint: disable=consider-using-with
            except FileExistsError:
                time.sleep(0.1)
            else:
                break
        try:
            self._dump(value, fd)
        except:  # noqa: E722
            temp.unlink()
            raise
        finally:
            fd.close()
        temp.replace(filename)

    def _set_max_age(self, filename: Path,
                     max_age: float | None = None) -> None:
        if max_age is None:
            max_age = _FILE_MAX_AGE
        now = time.time()
        os.utime(filename, times=(now, now + max_age))

    def _get_fresh_key_filename(self, mkey: Any) -> Path | None:
        filename = self._get_filename(mkey)
        return self._get_fresh_filename(filename)

    def _get_fresh_filename(self, filename: Path) -> Path | None:
        try:
            mtime = filename.stat().st_mtime
        except FileNotFoundError:
            return None

        if mtime < time.time():
            filename.unlink()
            return None

        return filename

    def _put(self, mkey: Any, value: Any,
             max_age: float | None = None) -> None:
        filename = self._get_filename(mkey)
        try:
            self._write(filename, value)
        except FileNotFoundError:
            filename.parent.mkdir(parents=True)
            self._write(filename, value)
        self._set_max_age(filename, max_age)

    def _get(self, mkey: Any) -> Any:
        filename = self._get_fresh_key_filename(mkey)
        if not filename:
            raise KeyError(mkey)
        with open(filename, 'rb') as fd:
            return self._load(fd)

    def _remove(self, mkey: Any) -> None:
        try:
            self._get_filename(mkey).unlink()
        except FileNotFoundError as ex:
            raise KeyError(mkey) from ex

    def _flush(self) -> None:
        if not self._cache_root.exists():
            return
        for path in self._cache_root.iterdir():
            if path.name.startswith(_DIR_PREFIX) and path.is_dir():
                shutil.rmtree(path)
            else:
                warnings.warn(f'Unexpected entry in cache directory: {path}')

    def _has(self, key: Any) -> bool:
        return self._get_fresh_key_filename(key) is not None

    def _gc_dir(self, path: Path) -> None:
        if not path.exists():
            return
        for entry in path.iterdir():
            if entry.is_dir():
                self._gc_dir(path / entry)
            else:
                self._get_fresh_filename(path / entry)

    def gc(self) -> None:
        """Delete expired cache files from the cache directory."""
        if not self._cache_root.exists():
            return
        self._gc_dir(self._cache_root)


Cache = FileCache
