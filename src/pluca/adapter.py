from collections.abc import Iterable, Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CacheAdapter(Protocol):
    """Adapter protocol used by ``pluca.Cache``.

    Optional optimization methods should raise ``NotImplementedError``
    when unsupported.
    """

    def put_mapped(self, mkey: Any, value: Any,
                   max_age: float | None = None) -> None:
        ...

    def get_mapped(self, mkey: Any) -> Any:
        ...

    def remove_mapped(self, mkey: Any) -> None:
        ...

    def flush(self) -> None:
        ...

    def has_mapped(self, mkey: Any) -> bool:
        ...

    def put_many_mapped(self,
                        data: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
                        max_age: float | None = None) -> None:
        ...

    def get_many_mapped(self, keys: Iterable[Any],
                        default: Any = ...) -> list[tuple[Any, Any]]:
        ...

    def remove_many_mapped(self, keys: Iterable[Any]) -> None:
        ...

    def gc(self) -> None:
        ...

    def shutdown(self) -> None:
        ...
