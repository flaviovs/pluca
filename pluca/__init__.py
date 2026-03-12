"""Pluggable Cache Architecture for Python."""
import abc
from functools import wraps, partial
from collections.abc import Callable, Iterable, Mapping
from typing import Any

__version__ = '0.6.2'


class CacheError(Exception):
    """Base exception type for cache-related errors."""


class Cache(abc.ABC):
    """Pluggable Cache Architecture (pluca) cache.

    This is the base pluca cache class. It is inherited to implement
    other cache back-ends. Use `help(MODULE.CLASS)` to get help about
    `MODULE.CLASS`.
    """

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
        if max_age and max_age < 0:
            raise ValueError('Cache max_age must be greater or equal to zero, '
                             f'got {max_age}')
        self._put(self._map_key(key), value, max_age)

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
            return self._get(self._map_key(key))
        except KeyError as ex:
            if default is Ellipsis:
                raise KeyError(key) from ex
        return default

    def gc(self) -> None:
        """Run cache garbage collection.

        Raises:
            NotImplementedError: If the backend does not support garbage
                collection.

        """
        raise NotImplementedError(f'{self.__class__.__qualname__} does not '
                                  'support garbage collection')

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
            return self._get(mkey)
        except KeyError:
            pass
        value = func()
        self._put(mkey, value, max_age)
        return value

    def _dumps(self, obj: Any) -> bytes:
        import pickle  # pylint: disable=import-outside-toplevel
        return pickle.dumps(obj)

    def _loads(self, data: bytes) -> Any:
        import pickle  # pylint: disable=import-outside-toplevel
        return pickle.loads(data)

    def _map_key(self, key: Any) -> str:
        import hashlib  # pylint: disable=import-outside-toplevel
        algo = hashlib.sha1()
        algo.update(repr((type(key), key)).encode('utf-8'))
        return algo.hexdigest()

    @abc.abstractmethod
    def _put(self, mkey: Any, value: Any,
             max_age: float | None = None) -> None:
        pass

    @abc.abstractmethod
    def _get(self, mkey: Any) -> Any:
        pass

    @abc.abstractmethod
    def _remove(self, mkey: Any) -> None:
        pass

    def remove(self, key: Any) -> None:
        """Remove a cache entry.

        Args:
            key: Entry key.

        Raises:
            KeyError: If the key does not exist.

        """
        try:
            self._remove(self._map_key(key))
        except KeyError as ex:
            raise KeyError(key) from ex

    def remove_many(self, keys: Iterable[Any]) -> None:
        """Remove multiple cache entries.

        Missing keys are ignored.

        Args:
            keys: Iterable of entry keys.

        """
        for key in keys:
            try:
                self.remove(key)
            except KeyError:
                pass

    @abc.abstractmethod
    def _flush(self) -> None:
        pass

    def flush(self) -> None:
        """Remove all entries from the cache."""
        self._flush()

    def _has(self, key: Any) -> bool:
        try:
            self._get(key)
            return True
        except KeyError:
            pass
        return False

    def has(self, key: Any) -> bool:
        """Check whether a key is present in the cache.

        Args:
            key: Entry key.

        Returns:
            ``True`` when the key exists, otherwise ``False``.

        """
        return self._has(self._map_key(key))

    def put_many(self,
                 data: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
                 max_age: float | None = None) -> None:
        """Store multiple entries in the cache.

        Args:
            data: Mapping or iterable of ``(key, value)`` pairs.
            max_age: Maximum age in seconds applied to all stored entries.

        """
        if isinstance(data, Mapping):
            data = data.items()
        for (key, value) in data:
            self.put(key, value, max_age)

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
        data = []
        for key in keys:
            try:
                value = self.get(key)
            except KeyError:
                if default is Ellipsis:
                    continue
                value = default
            data.append((key, value))
        return data

    def shutdown(self) -> None:
        """Shutdown the cache.

        Shuts down the cache. This releases all the resources used by
        the cache. A cache object that has been shut down cannot be
        used anymore.

        """

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
