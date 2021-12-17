from typing import Optional, Any

from pluca import Adapter as CacheAdapter, Cache


class Adapter(CacheAdapter):

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
    return Cache(Adapter())
