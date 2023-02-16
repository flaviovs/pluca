import time
from typing import Any, Optional, NamedTuple

import pluca


class _Entry(NamedTuple):
    value: Any
    expires: Optional[float]

    @property
    def is_fresh(self) -> bool:
        return self.expires is None or self.expires > time.time()


class DbmCache(pluca.Cache):
    """DBM cache for pluca.

    This cache store entries in DBM files. It uses Python's [DBM
    database interface](https://docs.python.org/3/library/dbm.html).

    Args:
        dbm: The DBM object.

    """

    def __init__(self, dbm: Any):
        self.dbm = dbm

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(dbm={self.dbm!r})'

    def _put(self, key: Any, value: Any,
             max_age: Optional[float] = None) -> None:
        self.dbm[key] = self._dumps(_Entry(value, max_age))

    def _get(self, key: Any) -> Any:
        entry = self._loads(self.dbm[key])
        if not entry.is_fresh:
            del self.dbm[key]
            raise KeyError(key)
        return entry.value

    def _remove(self, key: Any) -> None:
        del self.dbm[key]

    def flush(self) -> None:
        for key in self.dbm.keys():
            del self.dbm[key]

    def _has(self, key: Any) -> bool:
        return key in self.dbm

    def gc(self) -> None:
        for key in self.dbm.keys():
            entry = self._loads(self.dbm[key])
            if not entry.is_fresh:
                del self.dbm[key]

        try:
            self.dbm.reorganize()
        except AttributeError:
            pass


Cache = DbmCache
