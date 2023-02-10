from typing import Optional, Any

import pluca


class CacheAdapter(pluca.CacheAdapter):
    """Null cache adapter for pluca.

    This is a cache adapter that does not persist entries: you can
    "store" data in it, but all "get" operations will fail.

    """

    def put(self, key: Any, data: Any, max_age: Optional[float] = None):
        pass

    def get(self, key: Any) -> Any:
        raise KeyError(key)

    def remove(self, key: Any) -> None:
        raise KeyError(key)

    def flush(self) -> None:
        pass

    def has(self, key: Any) -> bool:
        return False

    def gc(self) -> None:
        pass


def create():
    return pluca.Cache(CacheAdapter())
