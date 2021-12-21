import abc
from typing import (Optional, Any, Iterable, Mapping, Callable,
                    Tuple, List, NoReturn)

__version__ = '0.1.1'


class CacheError(Exception):
    pass


class CacheAdapter(abc.ABC):

    def _dumps(self, obj: Any) -> bytes:
        import pickle
        return pickle.dumps(obj)

    def _loads(self, data: bytes) -> Any:
        import pickle
        return pickle.loads(data)

    def _get_cache_key(self, key: Any) -> Any:
        import hashlib
        algo = hashlib.sha1()
        algo.update(str(key).encode('utf-8'))
        return algo.hexdigest()

    @abc.abstractclassmethod
    def put(self, key: Any, value: Any,
            max_age: Optional[float] = None) -> None:
        pass

    @abc.abstractclassmethod
    def get(self, key: Any) -> Any:
        pass

    def has(self, key: Any) -> bool:
        try:
            self.get(key)
            return True
        except KeyError:
            pass
        return False

    @abc.abstractclassmethod
    def remove(self, key: Any) -> None:
        pass

    @abc.abstractclassmethod
    def flush(self) -> None:
        pass

    def put_many(self, data: Iterable[Tuple[Any, Any]],
                 max_age: Optional[float] = None) -> None:
        for (k, v) in data:
            self.put(k, v, max_age)

    def get_many(self, keys: Iterable[Any],
                 default: Any = None) -> List[Tuple[Any, Any]]:
        data = []
        for k in keys:
            try:
                value = self.get(k)
            except KeyError:
                if default is None:
                    continue
                value = default
            data.append((k, value))
        return data

    def gc(self) -> Optional[NoReturn]:
        raise NotImplementedError(f'{self.__class__.__qualname__} does not '
                                  'support garbage collection')


class Cache(abc.ABC):
    def __init__(self, adapter: CacheAdapter):
        super().__init__()
        self._adapter = adapter

    def flush(self):
        self._adapter.flush()

    def has(self, key: Any) -> bool:
        return self._adapter.has(key)

    def put(self, key: Any, value: Any,
            max_age: Optional[float] = None) -> None:
        self._adapter.put(key, value, max_age)

    def get(self, key: Any, default: Any = None) -> Any:
        try:
            return self._adapter.get(key)
        except KeyError:
            if default is None:
                raise
        return default

    def remove(self, key: Any) -> None:
        self._adapter.remove(key)

    def gc(self) -> None:
        self._adapter.gc()

    def get_put(self, key: Any, func: Callable[[], Any],
                max_age: Optional[float] = None) -> Any:
        try:
            return self.get(key)
        except KeyError:
            pass
        value = func()
        self.put(key, value, max_age)
        return value

    def put_many(self,
                 data: Mapping[Any, Any],
                 max_age: Optional[float] = None) -> None:
        self._adapter.put_many(data, max_age)

    def get_many(self,
                 keys: Iterable[Any],
                 default: Any = None) -> List[Tuple[Any, Any]]:
        return self._adapter.get_many(keys, default)

    @property
    def adapter(self):
        return self._adapter
