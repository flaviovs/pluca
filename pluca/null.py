from typing import Optional, Any, Hashable

import pluca


class CacheAdapter(pluca.CacheAdapter):
    """Null cache adapter for pluca.

    This is a cache adapter that does not persist entries: you can
    "store" data in it, but all "get" operations will fail.

    """

    def put(self, key: Hashable, value: Any,
            max_age: Optional[float] = None) -> None:
        pass

    def get(self, key: Hashable) -> Any:
        raise KeyError(key)

    remove = get

    def has(self, key: Hashable) -> bool:
        return False

    def flush(self) -> None:
        pass

    gc = flush


def create() -> pluca.Cache:
    return pluca.Cache(CacheAdapter())
