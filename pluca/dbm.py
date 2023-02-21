import time
import dbm
from pathlib import Path
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

    You call instantiate DBM caches with either an existing DMB file
    handle, or a file name. In the latter case, the file will be
    created if it does not exist.

    Args:
        db: The DBM object, or a database file name.

    """

    def __init__(self, db: Any):
        if isinstance(db, str):
            self.dbm = dbm.open(db, 'c')
        elif isinstance(db, Path):
            self.dbm = dbm.open(str(db), 'c')
        else:
            self.dbm = db

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(dbm={self.dbm!r})'

    def _put(self, mkey: Any, value: Any,
             max_age: Optional[float] = None) -> None:
        self.dbm[mkey] = self._dumps(_Entry(value,
                                            time.time() + max_age
                                            if max_age else None))

    def _get(self, mkey: Any) -> Any:
        entry = self._loads(self.dbm[mkey])
        if not entry.is_fresh:
            del self.dbm[mkey]
            raise KeyError(mkey)
        return entry.value

    def _remove(self, mkey: Any) -> None:
        del self.dbm[mkey]

    def _flush(self) -> None:
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
            self.dbm.reorganize()  # type: ignore [attr-defined]
        except AttributeError:
            pass

    def shutdown(self) -> None:
        self.dbm.close()


Cache = DbmCache
