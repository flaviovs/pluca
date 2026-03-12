from collections.abc import Iterable, Mapping
import dbm
import pickle
import time
from pathlib import Path
from typing import Any, NamedTuple


class _Entry(NamedTuple):
    value: Any
    expires: float | None

    @property
    def is_fresh(self) -> bool:
        return self.expires is None or self.expires > time.time()


class DbmAdapter:
    """DBM cache adapter for pluca."""

    def __init__(self, db: Any):
        if isinstance(db, str):
            self.dbm = dbm.open(db, 'c')
        elif isinstance(db, Path):
            self.dbm = dbm.open(str(db), 'c')
        else:
            self.dbm = db

    def put_mapped(self, mkey: Any, value: Any,
                   max_age: float | None = None) -> None:
        expires = None if max_age is None else time.time() + max_age
        self.dbm[mkey] = pickle.dumps(_Entry(value, expires))

    def get_mapped(self, mkey: Any) -> Any:
        entry = pickle.loads(self.dbm[mkey])
        if not entry.is_fresh:
            del self.dbm[mkey]
            raise KeyError(mkey)
        return entry.value

    def remove_mapped(self, mkey: Any) -> None:
        del self.dbm[mkey]

    def flush(self) -> None:
        for key in self.dbm.keys():
            del self.dbm[key]

    def has_mapped(self, mkey: Any) -> bool:
        return mkey in self.dbm

    def put_many_mapped(self,
                        data: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
                        max_age: float | None = None) -> None:
        raise NotImplementedError

    def get_many_mapped(self, keys: Iterable[Any],
                        default: Any = ...) -> list[tuple[Any, Any]]:
        raise NotImplementedError

    def remove_many_mapped(self, keys: Iterable[Any]) -> None:
        raise NotImplementedError

    def gc(self) -> None:
        """Delete expired entries and compact the DBM store when possible."""
        for key in self.dbm.keys():
            entry = pickle.loads(self.dbm[key])
            if not entry.is_fresh:
                del self.dbm[key]

        try:
            self.dbm.reorganize()  # type: ignore[attr-defined]
        except AttributeError:
            pass

    def shutdown(self) -> None:
        """Close the underlying DBM database handle."""
        self.dbm.close()


Adapter = DbmAdapter
