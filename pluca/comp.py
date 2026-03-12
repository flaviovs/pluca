from collections.abc import Callable, Iterable, Mapping
from typing import Any

import pluca
from pluca.utils import create_cache


class CompositeCache(pluca.Cache):
    """Composite cache for pluca.

    The composite cache allows to chain many caches into one. When a
    cache entry is added to the composite cache, it is added to all
    caches in the chain. When a call to get entries are called, the
    first cache that has the entry is selected, and the cached data is
    retrieved from it.

    You can use this, for example, to chain a faster but perhaps more
    resource intensive cache with another one that is slower but more
    resource friendly.

    Example:

        >>> import pluca.comp
        >>> import pluca.file
        >>> import pluca.memory
        >>>
        >>> cache = pluca.comp.Cache()

        Now let's add a fast memory cache first. Limit the number of
        entries to avoid high memory usage:

        >>> cache.add_cache(pluca.memory.Cache(max_entries=1_000))

        Also add a file cache to persist the entries:

        >>> cache.add_cache(pluca.file.Cache())

        Now add a cache entry. The entry will be stored in both
        caches:

        >>> cache.put('foo', 'bar')

        Fetch the entry. Although it can't be seen here, the entry is
        fetched from the first cache that has the key, a memory cache
        in our this case.

        >>> cache.get('foo')
        'bar'

    You can create a composite cache by passing a list of cache
    specification mappings to the composite cache constructor.

    Example:

        cache = pluca.comp.Cache([{
            'factory' => 'pluca.memory']

    See `add_cache_config()` for details about cache specification
    mappings.

    Args:
        config: List of cache configuration entries.
        allowed_class_modules: Optional tuple of allowed module prefixes used
            to validate configured ``factory`` paths before importing.

    """

    def __init__(self,
                 config: Iterable[Mapping[str, Any]] | None = None,
                 allowed_class_modules: tuple[str, ...] | None = None) -> None:
        self._caches: list[pluca.Cache] = []
        self._allowed_class_modules = allowed_class_modules

        if config:
            for cfg in config:
                self.add_cache_config(cfg)

    def add_cache_config(
            self,
            config: Mapping[str, Any],
            allowed_class_modules: tuple[str, ...] | None = None) -> None:
        """Add a cache via configuration.

        This adds a cache entry from a cache specification mapping
        (i.e. a dict). The mapping must have a `factory` attribute with
        a cache factory path in ``"module:factory"`` format. If
        ``:factory`` is omitted, ``:Cache`` is assumed. All other keys
        in the dict are passed to the factory function as named
        arguments.

        Example:

            >>> import pluca.comp
            >>>
            >>> cache = pluca.comp.Cache()
            >>>
            >>> cache.add_cache_config({
            ...     'factory': 'pluca.memory',
            ...     'max_entries': 1_000,
            ... })
            >>> cache.add_cache_config({
            ...     'factory': 'pluca.file',
            ...     'name': 'mycache',
            ... })

        Args:
            config: Cache specification mapping.
            allowed_class_modules: Optional tuple of allowed module prefixes
                used to validate configured ``factory`` paths before importing.

        """
        config = dict(config)
        factory = config.pop('factory')
        if allowed_class_modules is None:
            allowed_class_modules = self._allowed_class_modules
        self.add_cache(create_cache(factory,
                                    allowed_modules=allowed_class_modules,
                                    **config))

    def add_cache(self, cache: pluca.Cache) -> None:
        """Add a cache.

        This adds a cache object to the composite cache.

        Args:
            cache: Cache to add.

        """
        self._caches.append(cache)

    @property
    def caches(self) -> list[pluca.Cache]:
        """Return a copy of configured child caches.

        Returns:
            A shallow copy of child cache instances.

        """
        return self._caches.copy()

    def _put(self, mkey: Any, value: Any,
             max_age: float | None = None) -> None:
        for cache in self._caches:
            # pylint: disable-next=protected-access
            cache._put(mkey, value, max_age)

    def _get(self, mkey: Any) -> Any:
        for cache in self._caches:
            try:
                return cache._get(mkey)  # pylint: disable=protected-access
            except KeyError:
                pass
        raise KeyError(mkey)

    def gc(self) -> None:
        """Run garbage collection on all child caches."""
        for cache in self._caches:
            cache.gc()

    def get_put(self, key: Any, func: Callable[[], Any],
                max_age: float | None = None) -> Any:
        """Get a value or compute and store it in all child caches.

        Args:
            key: Entry key.
            func: Callable used to compute the value on cache miss.
            max_age: Maximum age in seconds for newly cached values.

        Returns:
            Cached or computed value.

        """
        mkey = self._map_key(key)
        try:
            return self._get(mkey)
        except KeyError:
            pass

        value = func()
        self.put(key, value, max_age)
        return value

    def _remove(self, mkey: Any) -> None:
        removed = False
        for cache in self._caches:
            try:
                cache._remove(mkey)  # pylint: disable=protected-access
            except KeyError:
                continue
            removed = True
        if not removed:
            raise KeyError(mkey)

    def remove_many(self, keys: Iterable[Any]) -> None:
        """Remove multiple keys from all child caches.

        Args:
            keys: Iterable of entry keys.

        """
        keys = tuple(keys)
        for cache in self._caches:
            cache.remove_many(keys)

    def _flush(self) -> None:
        for cache in self._caches:
            cache.flush()

    def has(self, key: Any) -> bool:
        """Check whether any child cache contains a key.

        Args:
            key: Entry key.

        Returns:
            ``True`` if any cache contains the key, else ``False``.

        """
        for cache in self._caches:
            if cache.has(key):
                return True
        return False

    def shutdown(self) -> None:
        """Shutdown all child caches and clear the chain."""
        for cache in self._caches:
            cache.shutdown()
        self._caches = []


Cache = CompositeCache
