"""Pluggable Cache Architecture for Python."""

import hashlib
from collections.abc import Callable, Iterable, Mapping
from functools import partial, wraps
from typing import Any

from .adapter import CacheAdapter

__version__ = '0.7.0'


class CacheError(Exception):
    """Base exception type for cache-related errors."""


class Cache:
    """Pluggable Cache Architecture (pluca) cache API."""

    def __init__(self, adapter: CacheAdapter) -> None:
        self._adapter = adapter

    def __getattr__(self, name: str) -> Any:
        return getattr(self._adapter, name)

    @property
    def adapter(self) -> CacheAdapter:
        """Return the adapter used by this cache."""
        return self._adapter

    def _map_key(self, key: Any) -> str:
        algo = hashlib.sha1()
        algo.update(repr((type(key), key)).encode('utf-8'))
        return algo.hexdigest()

    def put(self, key: Any, value: Any,
            max_age: float | None = None) -> None:
        """Store a value in the cache.

        Args:
            key: Entry key.
            value: Value to cache.
            max_age: Maximum age in seconds. If ``None``, the entry does not
                expire.

        Raises:
            ValueError: If ``max_age`` is negative.

        """
        if max_age is not None and max_age < 0:
            raise ValueError('Cache max_age must be greater or equal to zero, '
                             f'got {max_age}')
        self._adapter.put_mapped(self._map_key(key), value, max_age)

    def get(self, key: Any, default: Any = ...) -> Any:
        """Get a value from the cache.

        Args:
            key: Entry key.
            default: Value returned when ``key`` is missing. If omitted,
                ``KeyError`` is raised.

        Returns:
            The cached value or ``default`` when provided.

        Raises:
            KeyError: If ``key`` does not exist and no default is provided.

        """
        try:
            return self._adapter.get_mapped(self._map_key(key))
        except KeyError as ex:
            if default is Ellipsis:
                raise KeyError(key) from ex
        return default

    def remove(self, key: Any) -> None:
        """Remove a cache entry.

        Args:
            key: Entry key.

        Raises:
            KeyError: If the key does not exist.

        """
        try:
            self._adapter.remove_mapped(self._map_key(key))
        except KeyError as ex:
            raise KeyError(key) from ex

    def flush(self) -> None:
        """Remove all entries from the cache."""
        self._adapter.flush()

    def has(self, key: Any) -> bool:
        """Check whether a key is present in the cache.

        Args:
            key: Entry key.

        Returns:
            ``True`` when the key exists, otherwise ``False``.

        """
        mkey = self._map_key(key)
        try:
            return self._adapter.has_mapped(mkey)
        except NotImplementedError:
            pass

        try:
            self._adapter.get_mapped(mkey)
            return True
        except KeyError:
            return False

    def put_many(self,
                 data: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
                 max_age: float | None = None) -> None:
        """Store multiple entries in the cache.

        Args:
            data: Mapping or iterable of ``(key, value)`` pairs.
            max_age: Maximum age in seconds applied to all stored entries.

        """
        if max_age is not None and max_age < 0:
            raise ValueError('Cache max_age must be greater or equal to zero, '
                             f'got {max_age}')

        mapped: tuple[tuple[Any, Any], ...]
        if isinstance(data, Mapping):
            mapped = tuple((self._map_key(key), value)
                           for (key, value) in data.items())
        else:
            mapped = tuple((self._map_key(key), value)
                           for (key, value) in data)

        try:
            self._adapter.put_many_mapped(mapped, max_age)
            return
        except NotImplementedError:
            pass

        for (mkey, value) in mapped:
            self._adapter.put_mapped(mkey, value, max_age)

    def get_many(self, keys: Iterable[Any],
                 default: Any = ...) -> list[tuple[Any, Any]]:
        """Get multiple values from the cache.

        Args:
            keys: Iterable of entry keys.
            default: Value returned for missing keys. If omitted, missing keys
                are omitted from the result.

        Returns:
            A list of ``(key, value)`` tuples.

        """
        all_keys = tuple(keys)
        mapped_keys = tuple(self._map_key(key) for key in all_keys)

        try:
            mapped_data = self._adapter.get_many_mapped(mapped_keys,
                                                        default=default)
            mapped_result = dict(mapped_data)
            result = []
            for key, mkey in zip(all_keys, mapped_keys):
                if mkey in mapped_result:
                    result.append((key, mapped_result[mkey]))
                elif default is not Ellipsis:
                    result.append((key, default))
            return result
        except NotImplementedError:
            pass

        result = []
        for key, mkey in zip(all_keys, mapped_keys):
            try:
                value = self._adapter.get_mapped(mkey)
            except KeyError:
                if default is Ellipsis:
                    continue
                value = default
            result.append((key, value))

        return result

    def remove_many(self, keys: Iterable[Any]) -> None:
        """Remove multiple cache entries.

        Missing keys are ignored.

        Args:
            keys: Iterable of entry keys.

        """
        mapped_keys = tuple(self._map_key(key) for key in keys)

        try:
            self._adapter.remove_many_mapped(mapped_keys)
            return
        except NotImplementedError:
            pass

        for mkey in mapped_keys:
            try:
                self._adapter.remove_mapped(mkey)
            except KeyError:
                pass

    def gc(self) -> None:
        """Run cache garbage collection."""
        self._adapter.gc()

    def get_put(self, key: Any, func: Callable[[], Any],
                max_age: float | None = None) -> Any:
        """Get a value or compute and store it when missing.

        Args:
            key: Entry key.
            func: Callable used to produce the value on cache miss.
            max_age: Maximum age in seconds for a newly stored value.

        Returns:
            Cached value when present, otherwise the value returned by
            ``func``.

        """
        mkey = self._map_key(key)
        try:
            return self._adapter.get_mapped(mkey)
        except KeyError:
            pass

        value = func()
        self._adapter.put_mapped(mkey, value, max_age)
        return value

    def shutdown(self) -> None:
        """Shutdown the cache.

        Shuts down the cache. This releases all the resources used by
        the cache. A cache object that has been shut down cannot be
        used anymore.

        """
        self._adapter.shutdown()

    def __call__(self, func: Callable[..., Any] | None = None,
                 max_age: int | None = None) -> Callable[..., Any]:
        """Wrap a callable with cache lookup and storage.

        Can be used directly as ``@cache`` or with options as
        ``@cache(max_age=...)``.

        Args:
            func: Callable to wrap.
            max_age: Maximum age in seconds for cached results.

        Returns:
            A wrapped callable that caches return values by arguments.

        """

        if func is None:
            return partial(self.__call__, max_age=max_age)

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:  # type: ignore[no-untyped-def]
            key = ('__pluca.decorator__', func.__qualname__,
                   args, sorted(kwargs.items()))
            try:
                return self.get(key)
            except KeyError:
                pass

            data = func(*args, **kwargs)
            self.put(key, data, max_age)
            return data

        return wrapper
