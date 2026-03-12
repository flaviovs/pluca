from collections.abc import Iterable, Mapping
from typing import Any

import pluca
from pluca.utils import create_cache


class CompositeAdapter:
    """Composite cache adapter for pluca."""

    def __init__(self,
                 config: Iterable[Mapping[str, Any]] | None = None,
                 allowed_class_modules: tuple[str, ...] | None = None) -> None:
        self._caches: list[pluca.Cache] = []
        self._allowed_class_modules = allowed_class_modules

        if config:
            for cfg in config:
                self.add_cache_config(cfg)

    def add_cache_config(
            self,
            config: Mapping[str, Any],
            allowed_class_modules: tuple[str, ...] | None = None) -> None:
        """Add a cache via configuration."""
        cfg = dict(config)
        factory = cfg.pop('factory')
        if allowed_class_modules is None:
            allowed_class_modules = self._allowed_class_modules
        self.add_cache(create_cache(factory,
                                    allowed_modules=allowed_class_modules,
                                    **cfg))

    def add_cache(self, cache: pluca.Cache) -> None:
        """Add a cache."""
        self._caches.append(cache)

    @property
    def caches(self) -> list[pluca.Cache]:
        """Return a copy of configured child caches."""
        return self._caches.copy()

    def put_mapped(self, mkey: Any, value: Any,
                   max_age: float | None = None) -> None:
        for cache in self._caches:
            cache.adapter.put_mapped(mkey, value, max_age)

    def get_mapped(self, mkey: Any) -> Any:
        for cache in self._caches:
            try:
                return cache.adapter.get_mapped(mkey)
            except KeyError:
                pass
        raise KeyError(mkey)

    def remove_mapped(self, mkey: Any) -> None:
        removed = False
        for cache in self._caches:
            try:
                cache.adapter.remove_mapped(mkey)
            except KeyError:
                continue
            removed = True
        if not removed:
            raise KeyError(mkey)

    def flush(self) -> None:
        for cache in self._caches:
            cache.flush()

    def has_mapped(self, mkey: Any) -> bool:
        for cache in self._caches:
            try:
                if cache.adapter.has_mapped(mkey):
                    return True
            except NotImplementedError:
                try:
                    cache.adapter.get_mapped(mkey)
                    return True
                except KeyError:
                    pass
        return False

    def put_many_mapped(self,
                        data: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
                        max_age: float | None = None) -> None:
        if isinstance(data, Mapping):
            items = tuple(data.items())
        else:
            items = tuple(data)

        for cache in self._caches:
            try:
                cache.adapter.put_many_mapped(items, max_age)
            except NotImplementedError:
                for mkey, value in items:
                    cache.adapter.put_mapped(mkey, value, max_age)

    def get_many_mapped(self, keys: Iterable[Any],
                        default: Any = ...) -> list[tuple[Any, Any]]:
        result = []
        for mkey in keys:
            found = False
            for cache in self._caches:
                try:
                    value = cache.adapter.get_mapped(mkey)
                except KeyError:
                    continue
                found = True
                result.append((mkey, value))
                break
            if not found and default is not Ellipsis:
                result.append((mkey, default))
        return result

    def remove_many_mapped(self, keys: Iterable[Any]) -> None:
        for mkey in keys:
            for cache in self._caches:
                try:
                    cache.adapter.remove_mapped(mkey)
                except KeyError:
                    continue

    def gc(self) -> None:
        """Run garbage collection on all child caches."""
        for cache in self._caches:
            cache.gc()

    def shutdown(self) -> None:
        """Shutdown all child caches and clear the chain."""
        for cache in self._caches:
            cache.shutdown()
        self._caches = []


Adapter = CompositeAdapter
