import abc
from functools import wraps, partial
from typing import (Optional, Any, Iterable, Mapping, Callable,
                    Dict, Hashable, NoReturn)

__version__ = '0.2.0'


class CacheError(Exception):
    pass


class CacheAdapter(abc.ABC):

    def _dumps(self, obj: Any) -> bytes:
        import pickle
        return pickle.dumps(obj)

    def _loads(self, data: bytes) -> Any:
        import pickle
        return pickle.loads(data)

    def _get_cache_key(self, key: Hashable) -> Any:
        import hashlib
        algo = hashlib.sha1()
        algo.update(repr((type(key), key)).encode('utf-8'))
        return algo.hexdigest()

    @abc.abstractclassmethod
    def put(self, key: Hashable, value: Any,
            max_age: Optional[float] = None) -> None:
        pass

    @abc.abstractclassmethod
    def get(self, key: Hashable) -> Any:
        pass

    def has(self, key: Hashable) -> bool:
        try:
            self.get(key)
            return True
        except KeyError:
            pass
        return False

    @abc.abstractclassmethod
    def remove(self, key: Hashable) -> None:
        pass

    @abc.abstractclassmethod
    def flush(self) -> None:
        pass

    def put_many(self, data: Mapping[Hashable, Any],
                 max_age: Optional[float] = None) -> None:
        for (k, v) in data.items():
            self.put(k, v, max_age)

    def get_many(self, keys: Iterable[Hashable],
                 default: Any = None) -> Dict[Hashable, Any]:
        data = {}
        for k in keys:
            try:
                value = self.get(k)
            except KeyError:
                if default is None:
                    continue
                value = default
            data[k] = value
        return data

    def gc(self) -> Optional[NoReturn]:
        raise NotImplementedError(f'{self.__class__.__qualname__} does not '
                                  'support garbage collection')


class Cache:
    """Pluggable Cache Architecture (pluca) cache interface.

    This is the pluca cache adapter interface. It contains all the
    logic to talk to specific cache adapters.

    Usually cache adapter modules provide a factory function (usually
    called `create()`) so that you do not need to instantiate `Cache`
    objects directly. For example, when using the file adapter, you
    can call `pluca.file.create(...)` to create a ready-to-use cache
    object using the file adapter.

    """

    def __init__(self, adapter: CacheAdapter):
        super().__init__()
        self._adapter = adapter

    def flush(self) -> None:
        self._adapter.flush()

    def has(self, key: Hashable) -> bool:
        return self._adapter.has(key)

    def put(self, key: Hashable, value: Any,
            max_age: Optional[float] = None) -> None:
        self._adapter.put(key, value, max_age)

    def get(self, key: Hashable, default: Any = None) -> Any:
        try:
            return self._adapter.get(key)
        except KeyError:
            if default is None:
                raise
        return default

    def remove(self, key: Hashable) -> None:
        self._adapter.remove(key)

    def gc(self) -> None:
        self._adapter.gc()

    def get_put(self, key: Hashable, func: Callable[[], Any],
                max_age: Optional[float] = None) -> Any:
        try:
            return self.get(key)
        except KeyError:
            pass
        value = func()
        self.put(key, value, max_age)
        return value

    def put_many(self,
                 data: Mapping[Hashable, Any],
                 max_age: Optional[float] = None) -> None:
        self._adapter.put_many(data, max_age)

    def get_many(self,
                 keys: Iterable[Hashable],
                 default: Any = None) -> Dict[Hashable, Any]:
        return self._adapter.get_many(keys, default)

    @property
    def adapter(self) -> CacheAdapter:
        return self._adapter

    def __call__(self, func: Callable = None, max_age: Optional[int] = None):

        if func is None:
            return partial(self.__call__, max_age=max_age)

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = ('__pluca.decorator__', func.__qualname__,
                   args, sorted(kwargs.items()))
            try:
                return self.get(key)
            except KeyError:
                pass
            data = func(*args, **kwargs)
            self.put(key, data, max_age)
            return data

        return wrapper
