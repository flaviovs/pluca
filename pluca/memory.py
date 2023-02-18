import sys
import time
from typing import Dict, Optional, Any, NamedTuple

import pluca


class _Entry(NamedTuple):
    data: Any
    expire: Optional[float]
    index_: int

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

    If `max_entries` is passed and the cache is full, then only one
    entry will be removed to make room for a new key by default. This
    keeps the most number of fresh entries available — which is good
    from a caching perspective — but performance gets a big hit when
    the limit is reached. You can compensate that by passing a higher
    number of entries to prune on the `prune` parameter.

    Args:
        max_entries: Optional number of maximum cache entries.
        prune: Number of entries to prune when the cache is full.

    """

    def __init__(self,
                 max_entries: Optional[int] = None,
                 prune: Optional[int] = None) -> None:
        if (max_entries is not None
                and prune is not None
                and (prune < 1 or prune > max_entries)):
            raise ValueError('prune must be greater than 0 '
                             'and less than max_entries')
        self.prune = prune
        self.max_entries = max_entries
        self._storage: Dict[Any, _Entry] = {}
        self._count: int = 0

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}(max_entries={self.max_entries!r}, '
                f'prune={self.prune})')

    def _put(self, key: Any, value: Any,
             max_age: Optional[float] = None) -> None:
        if key not in self._storage:
            self._count += 1
        self._storage[key] = _Entry(
            data=self._dumps(value),
            expire=(time.time() + max_age if max_age else None),
            index_=self._count)
        if (self.max_entries is not None
                and self._count > self.max_entries):
            self._gc()
            self._prune()

    def _prune(self) -> None:
        assert self.max_entries is not None

        items = sorted(self._storage.items(),
                       key=lambda x: (x[1].expire or sys.float_info.max,
                                      x[1].index_),
                       reverse=True)
        self._storage = {}
        self._count = 0

        max_entries = self.max_entries - (self.prune or 1)

        for (key, item) in items:
            self._count += 1
            self._storage[key] = item
            if self._count > max_entries:
                break

    def _get(self, key: Any) -> Any:
        entry = self._storage[key]
        if not entry.is_fresh:
            del self._storage[key]
            self._count -= 1
            raise KeyError(key)
        return self._loads(entry.data)

    def _remove(self, key: Any) -> None:
        entry = self._storage[key]
        del self._storage[key]
        self._count -= 1
        if not entry.is_fresh:
            raise KeyError(key)

    def flush(self) -> None:
        self._storage = {}
        self._count = 0

    def _has(self, key: Any) -> bool:
        return key in self._storage

    def _gc(self) -> None:
        self._storage = {k: e for k, e in self._storage.items() if e.is_fresh}
        self._count = len(self._storage)

    def gc(self) -> None:
        self._gc()
        if (self.max_entries is not None
                and self._count > self.max_entries):
            self._prune()

    shutdown = flush


Cache = MemoryCache
