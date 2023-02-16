import time
from typing import Dict, Optional, Any, NamedTuple

import pluca


class _Entry(NamedTuple):
    data: Any
    expire: float

    @property
    def is_fresh(self) -> bool:
        return self.expire is None or self.expire > time.time()


class MemoryCache(pluca.Cache):
    """Memory cache for pluca.

    A cache that stores cache entries in the program memory. All
    entries are lost when the instance is removed.

    By default there is no limit on the number of entries kept in the
    cache. You can change that by specifying a maximum number of
    entries in the `max_entries` parameter.

    Args:
        max_entries: Optional number of maximum cache entries.

    """

    def __init__(self, max_entries: Optional[int] = None) -> None:
        self.max_entries = max_entries
        self._storage: Dict[Any, _Entry] = {}

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(max_entries={self.max_entries!r})'

    def _put(self, key: Any, value: Any,
             max_age: Optional[float] = None) -> None:
        self._storage[key] = _Entry(
            data=value,
            expire=(time.time() + max_age if max_age else float('inf')))
        if (self.max_entries is not None
                and len(self._storage) > self.max_entries):
            self._prune()

    def _prune(self) -> None:
        assert self.max_entries is not None

        self.gc()

        items = sorted(self._storage.items(),
                       key=lambda x: x[1].expire,
                       reverse=True)
        self._storage = {}
        nr = 0
        for (key, item) in items:
            self._storage[key] = item
            nr += 1
            if nr >= self.max_entries:
                break

    def _get(self, key: Any) -> Any:
        entry = self._storage[key]
        if not entry.is_fresh:
            del self._storage[key]
            raise KeyError(key)
        return entry.data

    def _remove(self, key: Any) -> None:
        entry = self._storage[key]
        del self._storage[key]
        if not entry.is_fresh:
            raise KeyError(key)

    def flush(self) -> None:
        self._storage = {}

    def _has(self, key: Any) -> bool:
        return key in self._storage

    def gc(self) -> None:
        self._storage = {k: e for k, e in self._storage.items() if e.is_fresh}


Cache = MemoryCache
