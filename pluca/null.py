from typing import Optional, Any

import pluca


class CacheAdapter(pluca.CacheAdapter):
    """Null cache adapter for pluca.

    This is a cache adapter that does not persist entries: you can
    "store" data in it, but all "get" operations will fail.

    """

    def put(self, key: Any, value: Any,
            max_age: Optional[float] = None) -> None:
        pass

    def get(self, key: Any) -> Any:
        raise KeyError(key)

    remove = get

    def has(self, key: Any) -> bool:
        return False

    def flush(self) -> None:
        pass

    gc = flush


def create():
    return pluca.Cache(CacheAdapter())
