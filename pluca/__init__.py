import abc
from functools import wraps, partial
from typing import (Optional, Any, Iterable, Mapping, Callable,
                    List, Tuple, NoReturn, Union)

__version__ = '0.2.0'


class CacheError(Exception):
    pass


class CacheAdapter(abc.ABC):

    def _dumps(self, obj: Any) -> bytes:
        import pickle  # pylint: disable=import-outside-toplevel
        return pickle.dumps(obj)

    def _loads(self, data: bytes) -> Any:
        import pickle  # pylint: disable=import-outside-toplevel
        return pickle.loads(data)

    def _map_key(self, key: Any) -> str:
        import hashlib  # pylint: disable=import-outside-toplevel
        algo = hashlib.sha1()
        algo.update(repr((type(key), key)).encode('utf-8'))
        return algo.hexdigest()

    @abc.abstractmethod
    def put(self, key: Any, value: Any,
            max_age: Optional[float] = None) -> None:
        pass

    @abc.abstractmethod
    def get(self, key: Any) -> Any:
        pass

    def has(self, key: Any) -> bool:
        try:
            self.get(key)
            return True
        except KeyError:
            pass
        return False

    @abc.abstractmethod
    def remove(self, key: Any) -> None:
        pass

    @abc.abstractmethod
    def flush(self) -> None:
        pass

    def put_many(self,
                 data: Union[Mapping[Any, Any], Iterable[Tuple[Any, Any]]],
                 max_age: Optional[float] = None) -> None:
        if isinstance(data, Mapping):
            data = data.items()
        for (k, v) in data:
            self.put(k, v, max_age)

    def get_many(self, keys: Iterable[Any],
                 default: Any = None) -> List[Tuple[Any, Any]]:
        data = []
        for key in keys:
            try:
                value = self.get(key)
            except KeyError:
                if default is None:
                    continue
                value = default
            data.append((key, value))
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
                 data: Union[Mapping[Any, Any], Iterable[Tuple[Any, Any]]],
                 max_age: Optional[float] = None) -> None:
        self._adapter.put_many(data, max_age)

    def get_many(self,
                 keys: Iterable[Any],
                 default: Any = None) -> List[Tuple[Any, Any]]:
        return self._adapter.get_many(keys, default)

    @property
    def adapter(self) -> CacheAdapter:
        return self._adapter

    def __call__(self, func: Optional[Callable[..., Any]] = None,
                 max_age: Optional[int] = None) -> Callable[..., Any]:

        if func is None:
            return partial(self.__call__, max_age=max_age)

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:  # type: ignore[no-untyped-def]
            assert func

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
