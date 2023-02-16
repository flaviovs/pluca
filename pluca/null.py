from typing import Optional, Any

import pluca


class NullCache(pluca.Cache):
    """Null cache for pluca.

    This is a cache that does not persist entries: you can "store"
    data in it, but all "get" operations will fail.

    """

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'

    def _put(self, key: Any, value: Any,
             max_age: Optional[float] = None) -> None:
        pass

    def _raise_keyerror(self, key: Any) -> Any:
        raise KeyError(key)

    _get = _raise_keyerror
    _remove = _raise_keyerror

    def _has(self, _key: Any) -> bool:
        return False

    def _pass(self) -> None:
        pass

    flush = _pass
    gc = _pass


Cache = NullCache
