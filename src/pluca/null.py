from collections.abc import Iterable, Mapping
from typing import Any


class NullAdapter:
    """Null cache adapter for pluca."""

    def put_mapped(self, mkey: Any, value: Any,
                   max_age: float | None = None) -> None:
        _ = (mkey, value, max_age)

    def get_mapped(self, mkey: Any) -> Any:
        raise KeyError(mkey)

    def remove_mapped(self, mkey: Any) -> None:
        raise KeyError(mkey)

    def flush(self) -> None:
        pass

    def has_mapped(self, mkey: Any) -> bool:
        _ = mkey
        return False

    def put_many_mapped(self,
                        data: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
                        max_age: float | None = None) -> None:
        _ = (data, max_age)

    def get_many_mapped(self, keys: Iterable[Any],
                        default: Any = ...) -> list[tuple[Any, Any]]:
        if default is Ellipsis:
            return []
        return [(key, default) for key in keys]

    def remove_many_mapped(self, keys: Iterable[Any]) -> None:
        _ = keys

    def gc(self) -> None:
        """Run cache garbage collection."""

    def shutdown(self) -> None:
        """Shutdown the cache adapter."""


Adapter = NullAdapter
