from collections.abc import Iterable, Mapping
import pickle
import sys
import time
from typing import Any, NamedTuple


class _Entry(NamedTuple):
    data: Any
    expire: float | None
    index_: int

    @property
    def is_fresh(self) -> bool:
        return self.expire is None or self.expire > time.time()


class MemoryAdapter:
    """Memory cache adapter for pluca."""

    def __init__(self,
                 max_entries: int | None = None,
                 prune: int | None = None) -> None:
        if (max_entries is not None
                and prune is not None
                and (prune < 1 or prune > max_entries)):
            raise ValueError('prune must be greater than 0 '
                             'and less than max_entries')
        self.prune = prune
        self.max_entries = max_entries
        self._storage: dict[Any, _Entry] = {}
        self._count = 0

    def put_mapped(self, mkey: Any, value: Any,
                   max_age: float | None = None) -> None:
        expire = None if max_age is None else time.time() + max_age
        if mkey not in self._storage:
            self._count += 1
        self._storage[mkey] = _Entry(
            data=pickle.dumps(value),
            expire=expire,
            index_=self._count)
        if (self.max_entries is not None
                and self._count > self.max_entries):
            self.gc()

    def _prune(self) -> None:
        assert self.max_entries is not None

        items = sorted(self._storage.items(),
                       key=lambda x: (x[1].expire or sys.float_info.max,
                                      x[1].index_),
                       reverse=True)
        self._storage = {}
        self._count = 0

        max_entries = self.max_entries - (self.prune or 1)

        for key, item in items:
            self._count += 1
            self._storage[key] = item
            if self._count > max_entries:
                break

    def get_mapped(self, mkey: Any) -> Any:
        entry = self._storage[mkey]
        if not entry.is_fresh:
            del self._storage[mkey]
            self._count -= 1
            raise KeyError(mkey)
        return pickle.loads(entry.data)

    def remove_mapped(self, mkey: Any) -> None:
        entry = self._storage[mkey]
        del self._storage[mkey]
        self._count -= 1
        if not entry.is_fresh:
            raise KeyError(mkey)

    def flush(self) -> None:
        self._storage = {}
        self._count = 0

    def has_mapped(self, mkey: Any) -> bool:
        return mkey in self._storage

    def put_many_mapped(self,
                        data: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
                        max_age: float | None = None) -> None:
        if isinstance(data, Mapping):
            data = data.items()
        for mkey, value in data:
            self.put_mapped(mkey, value, max_age)

    def get_many_mapped(self, keys: Iterable[Any],
                        default: Any = ...) -> list[tuple[Any, Any]]:
        data = []
        for mkey in keys:
            try:
                value = self.get_mapped(mkey)
            except KeyError:
                if default is Ellipsis:
                    continue
                value = default
            data.append((mkey, value))
        return data

    def remove_many_mapped(self, keys: Iterable[Any]) -> None:
        for mkey in keys:
            try:
                self.remove_mapped(mkey)
            except KeyError:
                pass

    def gc(self) -> None:
        """Delete expired entries and enforce entry limits."""
        self._storage = {k: e for k, e in self._storage.items() if e.is_fresh}
        self._count = len(self._storage)
        if (self.max_entries is not None
                and self._count > self.max_entries):
            self._prune()

    def shutdown(self) -> None:
        """Shutdown the cache adapter."""
        self.flush()


Adapter = MemoryAdapter
