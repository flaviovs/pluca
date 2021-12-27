import importlib
from typing import Union, Callable, Dict, Optional

from pluca import Cache

_CACHES: Dict[str, Cache] = {}


def add(cache: str, factory: Union[str, Callable], *args, **kwargs) -> None:
    if cache in _CACHES:
        raise ValueError(f'A cache named {cache!r} already exists')

    if isinstance(factory, str):
        parts = factory.rsplit('.', 1)
        if len(parts) < 2:
            raise ValueError('Factory callable must be MODULE.FUNC')
        mod = importlib.import_module(parts[0])
        factory = getattr(mod, parts[1])

    assert callable(factory)
    _CACHES[cache] = factory(*args, **kwargs)


def get(cache: Optional[str] = None) -> Cache:
    if not cache:
        cache = 'default'
        if cache not in _CACHES:
            basic_config()
    return _CACHES[cache]


def remove(cache: str) -> None:
    del _CACHES[cache]


def remove_all() -> None:
    _CACHES.clear()


def basic_config(factory: str = 'pluca.file.create', *args, **kwargs) -> None:
    add('default', factory, *args, **kwargs)
