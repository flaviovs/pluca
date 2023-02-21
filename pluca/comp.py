from typing import Iterable, Mapping, List, Any, Optional, Callable

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
            'class' => 'pluca.memory.Cache']

    See `add_cache_config()` for details about cache specification
    mappings.

    Args:
        config: List of cache configuration entries.

    """

    def __init__(self,
                 config: Optional[Iterable[Mapping[str, Any]]] = None) -> None:
        self._caches: List[pluca.Cache] = []

        if config:
            for cfg in config:
                self.add_cache_config(cfg)

    def add_cache_config(self, config: Mapping[str, Any]) -> None:
        """Add a cache via configuration.

        This adds a cache entry from a cache specification mapping
        (i.e. a dict). The mapping must have a `class` attribute with
        the fully qualified callable name of a factory function to
        create the cache. All other keys in the dict are passed to the
        factory function as named arguments.

        Example:

            >>> import pluca.comp
            >>>
            >>> cache = pluca.comp.Cache()
            >>>
            >>> cache.add_cache_config({
            ...     'class': 'pluca.memory.Cache',
            ...     'max_entries': 1_000,
            ... })
            >>> cache.add_cache_config({
            ...     'class': 'pluca.file.Cache',
            ...     'name': 'mycache',
            ... })

        Args:
            config: Cache specification mapping.

        """
        config = dict(config)
        cls = config.pop('class')
        self.add_cache(create_cache(cls, **config))

    def add_cache(self, cache: pluca.Cache) -> None:
        """Add a cache.

        This adds a cache object to the composite cache.

        Args:
            cache: Cache to add.

        """
        self._caches.append(cache)

    @property
    def caches(self) -> List[pluca.Cache]:
        return self._caches.copy()

    def _put(self, mkey: Any, value: Any,
             max_age: Optional[float] = None) -> None:
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
        for cache in self._caches:
            cache.gc()

    def get_put(self, key: Any, func: Callable[[], Any],
                max_age: Optional[float] = None) -> Any:
        mkey = self._map_key(key)
        try:
            return self._get(mkey)
        except KeyError:
            pass

        value = func()
        self.put(key, value, max_age)
        return value

    def _remove(self, mkey: Any) -> None:
        for cache in self._caches:
            cache._remove(mkey)  # pylint: disable=protected-access

    def remove_many(self, keys: Iterable[Any]) -> None:
        keys = tuple(keys)
        for cache in self._caches:
            cache.remove_many(keys)

    def _flush(self) -> None:
        for cache in self._caches:
            cache.flush()

    def has(self, key: Any) -> bool:
        for cache in self._caches:
            if cache.has(key):
                return True
        return False

    def shutdown(self) -> None:
        for cache in self._caches:
            cache.shutdown()
        self._caches = []


Cache = CompositeCache
