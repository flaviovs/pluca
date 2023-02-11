import time
from dataclasses import dataclass
from typing import Dict, Optional, Any, NamedTuple, Hashable

import pluca


class _Entry(NamedTuple):
    data: Any
    expire: Optional[float]

    @property
    def is_fresh(self) -> bool:
        return self.expire is None or self.expire > time.time()


@dataclass
class CacheAdapter(pluca.CacheAdapter):
    """Memory cache adapter for pluca.

    Store cache entries in the program memory. All entries are lost
    when the program exits.

    By default there is no limit on the number of entries kept in the
    cache. You can change that by specifying a maximum number of
    entries in the `max_entries` parameter.

    Args:
        max_entries: Optional number of maximum cache entries.

    """

    max_entries: Optional[int] = None

    def __post_init__(self):
        self._storage: Dict[Hashable, Any] = {}

    def put(self, key: Hashable, data: Any,
            max_age: Optional[float] = None) -> None:
        self._storage[self._get_cache_key(key)] = _Entry(
            data=data,
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
        for (k, item) in items:
            self._storage[k] = item
            nr += 1
            if nr >= self.max_entries:
                break

    def get(self, key: Hashable) -> Any:
        skey = self._get_cache_key(key)
        entry = self._storage[skey]
        if not entry.is_fresh:
            del self._storage[skey]
            raise KeyError(key)
        return entry.data

    def remove(self, key: Hashable) -> None:
        skey = self._get_cache_key(key)
        try:
            entry = self._storage[skey]
        except KeyError as ex:
            raise KeyError(key) from ex
        del self._storage[skey]
        if not entry.is_fresh:
            raise KeyError(key)

    def flush(self) -> None:
        self._storage = {}

    def has(self, key: Hashable) -> bool:
        return self._get_cache_key(key) in self._storage

    def gc(self) -> None:
        self._storage = {k: e for k, e in self._storage.items() if e.is_fresh}


def create(max_entries: Optional[int] = None) -> pluca.Cache:
    return pluca.Cache(CacheAdapter(max_entries=max_entries))
