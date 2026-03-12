import warnings
import os
import socket
import time
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from typing import Any, BinaryIO, cast

import pluca

_FILE_MAX_AGE = 1_000_000_000

_DIR_PREFIX = 'cache-'

_MKDIR_STALE_AGE = 300.0
_MKDIR_WAIT_TIMEOUT = 30.0
_MKDIR_POLL_INTERVAL = 0.05


def _resolve_locking(locking: str | None) -> str | None:
    if locking is None:
        return None

    locking = locking.lower()

    if locking == 'none':
        return None

    if locking == 'auto':
        return 'msvcrt' if os.name == 'nt' else 'flock'

    if locking == 'flock':
        if os.name == 'nt':
            raise ValueError('locking="flock" is not supported on Windows')
        return 'flock'

    if locking == 'msvcrt':
        if os.name != 'nt':
            raise ValueError('locking="msvcrt" is only supported on Windows')
        return 'msvcrt'

    if locking == 'mkdir':
        return 'mkdir'

    raise ValueError('Invalid locking mechanism. Supported values are '
                     '"auto", "flock", "msvcrt", "mkdir", or None')


def _validate_positive_float(name: str, value: float | None) -> None:
    if value is None:
        return
    if value <= 0:
        raise ValueError(f'{name} must be greater than zero')


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
        locking: File locking mechanism name. Use ``'auto'`` to select the
            best mechanism for the current OS, or ``None`` to disable locking.
        mkdir_stale_age: Maximum age (seconds) for ``locking='mkdir'`` lock
            directories before stale reclamation is attempted.
        mkdir_wait_timeout: Maximum time (seconds) to wait for
            ``locking='mkdir'`` lock acquisition before raising
            ``TimeoutError``. Set ``None`` to wait indefinitely.
        mkdir_poll_interval: Polling interval (seconds) used when waiting on
            existing ``locking='mkdir'`` lock directories.

    """

    def __init__(self, name: str = 'pluca',
                 cache_dir: Path | None = None,
                 locking: str | None = 'auto',
                 mkdir_stale_age: float | None = _MKDIR_STALE_AGE,
                 mkdir_wait_timeout: float | None = _MKDIR_WAIT_TIMEOUT,
                 mkdir_poll_interval: float = _MKDIR_POLL_INTERVAL) -> None:

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
        self.locking = _resolve_locking(locking)
        _validate_positive_float('mkdir_stale_age', mkdir_stale_age)
        _validate_positive_float('mkdir_wait_timeout', mkdir_wait_timeout)
        _validate_positive_float('mkdir_poll_interval', mkdir_poll_interval)
        self.mkdir_stale_age = mkdir_stale_age
        self.mkdir_wait_timeout = mkdir_wait_timeout
        self.mkdir_poll_interval = mkdir_poll_interval
        self._hostname = socket.gethostname()

        self.name = name
        self.cache_dir = cache_dir

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}'
                f'(name={self.name!r}, '
                f'cache_dir={self.cache_dir!r}, '
                f'locking={self.locking!r}, '
                f'mkdir_stale_age={self.mkdir_stale_age!r}, '
                f'mkdir_wait_timeout={self.mkdir_wait_timeout!r}, '
                f'mkdir_poll_interval={self.mkdir_poll_interval!r})')

    def _dump(self, obj: Any, fd: BinaryIO) -> None:
        import pickle  # pylint: disable=import-outside-toplevel
        pickle.dump(obj, fd)

    def _load(self, fd: BinaryIO) -> Any:
        import pickle  # pylint: disable=import-outside-toplevel
        return pickle.load(fd)

    def _get_filename(self, mkey: str) -> Path:
        return (self._cache_root
                / f'{_DIR_PREFIX}{mkey[0:2]}' / f'{mkey[2:]}.dat')

    @contextmanager
    def _lock_entry(self, filename: Path,
                    shared: bool,
                    create: bool = False) -> Iterator[BinaryIO | None]:
        if self.locking is None:
            yield None
            return

        if create and not filename.parent.exists():
            filename.parent.mkdir(parents=True)

        mode = 'a+b' if create else 'r+b'

        try:
            fd = open(filename, mode)
        except FileNotFoundError:
            yield None
            return

        try:
            if self.locking == 'flock':
                import fcntl  # pylint: disable=import-outside-toplevel
                lock_mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
                fcntl.flock(fd.fileno(), lock_mode)
                try:
                    yield cast(BinaryIO, fd)
                finally:
                    fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
                return

            if self.locking == 'msvcrt':
                import importlib  # pylint: disable=import-outside-toplevel
                msvcrt = importlib.import_module('msvcrt')
                fd.seek(0)
                getattr(msvcrt, 'locking')(
                    fd.fileno(),
                    getattr(msvcrt, 'LK_LOCK'),
                    1)
                try:
                    yield cast(BinaryIO, fd)
                finally:
                    fd.seek(0)
                    getattr(msvcrt, 'locking')(
                        fd.fileno(),
                        getattr(msvcrt, 'LK_UNLCK'),
                        1)
                return

            raise RuntimeError(f'Unexpected locking value: {self.locking!r}')
        finally:
            fd.close()

    @contextmanager
    def _lock_entry_mkdir(self,
                          filename: Path,
                          create: bool = False) -> Iterator[None]:
        lock_dir = Path(f'{filename}.lock')
        owner = lock_dir / 'owner'

        start = time.monotonic()

        if not create and not lock_dir.parent.exists():
            yield
            return

        def _write_owner() -> None:
            owner.write_text(
                f'{os.getpid()}\n{self._hostname}\n{time.time()}\n',
                encoding='utf-8')

        def _read_owner() -> tuple[int | None, str | None, float | None]:
            try:
                data = owner.read_text(encoding='utf-8').splitlines()
                if len(data) < 3:
                    raise ValueError('invalid owner format')
                return int(data[0]), data[1], float(data[2])
            except (FileNotFoundError, ValueError):
                try:
                    created_at = lock_dir.stat().st_mtime
                except FileNotFoundError:
                    return None, None, None
                return None, None, created_at

        def _pid_alive(pid: int) -> bool:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
            except OSError:
                return False
            return True

        def _can_reclaim() -> bool:
            if self.mkdir_stale_age is None:
                return False

            pid, host, created_at = _read_owner()
            if created_at is None:
                return False

            age = time.time() - created_at
            if age < self.mkdir_stale_age:
                return False

            if pid is not None and host == self._hostname and _pid_alive(pid):
                return False

            return True

        def _reclaim() -> None:
            try:
                owner.unlink(missing_ok=True)
                lock_dir.rmdir()
            except OSError:
                pass

        while True:
            try:
                lock_dir.mkdir()
            except FileNotFoundError:
                if not create:
                    yield
                    return
                lock_dir.parent.mkdir(parents=True)
            except FileExistsError as ex:
                if _can_reclaim():
                    _reclaim()
                    continue

                timed_out = (
                    self.mkdir_wait_timeout is not None
                    and time.monotonic() - start > self.mkdir_wait_timeout)
                if timed_out:
                    raise TimeoutError(
                        f'Could not acquire lock directory: {lock_dir}'
                    ) from ex
                time.sleep(self.mkdir_poll_interval)
            else:
                _write_owner()
                break

        try:
            yield
        finally:
            owner.unlink(missing_ok=True)
            lock_dir.rmdir()

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

    def _is_expired(self, filename: Path) -> bool:
        try:
            return filename.stat().st_mtime < time.time()
        except FileNotFoundError:
            return True

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

        if self.locking == 'mkdir':
            with self._lock_entry_mkdir(filename, create=True):
                try:
                    self._write(filename, value)
                except FileNotFoundError:
                    filename.parent.mkdir(parents=True)
                    self._write(filename, value)
                self._set_max_age(filename, max_age)
            return

        if self.locking is None:
            try:
                self._write(filename, value)
            except FileNotFoundError:
                filename.parent.mkdir(parents=True)
                self._write(filename, value)
            self._set_max_age(filename, max_age)
            return

        with self._lock_entry(filename, shared=False, create=True) as fd:
            if fd is None:
                raise RuntimeError('Failed to acquire entry file for write')
            fd.seek(0)
            fd.truncate(0)
            self._dump(value, fd)
            fd.flush()
            self._set_max_age(filename, max_age)

    def _get(self, mkey: Any) -> Any:
        filename = self._get_filename(mkey)

        if self.locking == 'mkdir':
            with self._lock_entry_mkdir(filename):
                fresh_filename = self._get_fresh_filename(filename)
                if not fresh_filename:
                    raise KeyError(mkey)
                with open(fresh_filename, 'rb') as fd:
                    return self._load(fd)

        if self.locking is None:
            fresh_filename = self._get_fresh_filename(filename)
            if not fresh_filename:
                raise KeyError(mkey)
            with open(fresh_filename, 'rb') as fd:
                return self._load(fd)

        with self._lock_entry(filename, shared=True) as fd:
            if fd is None:
                raise KeyError(mkey)
            expired = self._is_expired(filename)
            if not expired:
                fd.seek(0)
                return self._load(fd)

        with self._lock_entry(filename, shared=False) as wfd:
            if wfd is not None and self._is_expired(filename):
                filename.unlink(missing_ok=True)
        raise KeyError(mkey)

    def _remove(self, mkey: Any) -> None:
        filename = self._get_filename(mkey)

        if self.locking == 'mkdir':
            with self._lock_entry_mkdir(filename):
                try:
                    filename.unlink()
                except FileNotFoundError as ex:
                    raise KeyError(mkey) from ex
            return

        if self.locking is None:
            try:
                filename.unlink()
            except FileNotFoundError as ex:
                raise KeyError(mkey) from ex
            return

        with self._lock_entry(filename, shared=False) as fd:
            if fd is None:
                raise KeyError(mkey)
            filename.unlink(missing_ok=True)

    def _flush(self) -> None:
        if not self._cache_root.exists():
            return
        for path in self._cache_root.iterdir():
            if path.name.startswith(_DIR_PREFIX) and path.is_dir():
                for entry in path.iterdir():
                    if entry.name.endswith('.lock') and entry.is_dir():
                        continue

                    if self.locking == 'mkdir':
                        with self._lock_entry_mkdir(entry):
                            entry.unlink(missing_ok=True)
                        continue

                    if self.locking is None:
                        entry.unlink(missing_ok=True)
                        continue
                    with self._lock_entry(entry, shared=False) as fd:
                        if fd is not None:
                            entry.unlink(missing_ok=True)
                for entry in path.iterdir():
                    if entry.name.endswith('.lock') and entry.is_dir():
                        entry.rmdir()
                path.rmdir()
            elif path.name == '.lock':
                # Backward compatibility for legacy cache-level lock files.
                path.unlink(missing_ok=True)
            else:
                warnings.warn(
                    f'Unexpected entry in cache directory: {path}')

    def _has(self, key: Any) -> bool:
        filename = self._get_filename(key)

        if self.locking == 'mkdir':
            with self._lock_entry_mkdir(filename):
                return self._get_fresh_filename(filename) is not None

        if self.locking is None:
            return self._get_fresh_filename(filename) is not None

        with self._lock_entry(filename, shared=True) as fd:
            if fd is None:
                return False
            if not self._is_expired(filename):
                return True

        with self._lock_entry(filename, shared=False) as wfd:
            if wfd is not None and self._is_expired(filename):
                filename.unlink(missing_ok=True)
        return False

    def _gc_dir(self, path: Path) -> None:
        if not path.exists():
            return
        for entry in path.iterdir():
            if entry.is_dir():
                self._gc_dir(path / entry)
            else:
                if entry.name.endswith('.lock'):
                    continue

                if self.locking == 'mkdir':
                    with self._lock_entry_mkdir(entry):
                        self._get_fresh_filename(path / entry)
                    continue

                if self.locking is None:
                    self._get_fresh_filename(path / entry)
                    continue
                with self._lock_entry(entry, shared=False) as fd:
                    if fd is not None and self._is_expired(entry):
                        entry.unlink(missing_ok=True)

    def gc(self) -> None:
        """Delete expired cache files from the cache directory."""
        if not self._cache_root.exists():
            return
        self._gc_dir(self._cache_root)


Cache = FileCache
