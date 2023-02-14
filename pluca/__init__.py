import abc
from functools import wraps, partial
from typing import (Optional, Any, Iterable, Mapping, Callable,
                    List, Tuple, Union)

__version__ = '0.3.0'


class CacheError(Exception):
    pass


class Cache(abc.ABC):
    """Pluggable Cache Architecture (pluca) cache.

    This is the base pluca cache class. It is inherited to implement
    other cache back-ends. Use `help(MODULE.CLASS)` to get help about
    `MODULE.CLASS`.
    """

    def put(self, key: Any, value: Any,
            max_age: Optional[float] = None) -> None:
        if max_age and max_age < 0:
            raise ValueError('Cache max_age must be greater or equal to zero, '
                             f'got {max_age}')
        self._put(self._map_key(key), value, max_age)

    def get(self, key: Any, default: Any = ...) -> Any:
        try:
            return self._get(self._map_key(key))
        except KeyError as ex:
            if default is Ellipsis:
                raise KeyError(key) from ex
        return default

    def gc(self) -> None:
        raise NotImplementedError(f'{self.__class__.__qualname__} does not '
                                  'support garbage collection')

    def get_put(self, key: Any, func: Callable[[], Any],
                max_age: Optional[float] = None) -> Any:
        mkey = self._map_key(key)
        try:
            return self._get(mkey)
        except KeyError:
            pass
        value = func()
        self._put(mkey, value, max_age)
        return value

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
    def _put(self, key: Any, value: Any,
             max_age: Optional[float] = None) -> None:
        pass

    @abc.abstractmethod
    def _get(self, key: Any) -> Any:
        pass

    @abc.abstractmethod
    def _remove(self, key: Any) -> None:
        pass

    def remove(self, key: Any) -> None:
        try:
            self._remove(self._map_key(key))
        except KeyError as ex:
            raise KeyError(key) from ex

    @abc.abstractmethod
    def flush(self) -> None:
        pass

    def _has(self, key: Any) -> bool:
        try:
            self._get(key)
            return True
        except KeyError:
            pass
        return False

    def has(self, key: Any) -> bool:
        return self._has(self._map_key(key))

    def put_many(self,
                 data: Union[Mapping[Any, Any], Iterable[Tuple[Any, Any]]],
                 max_age: Optional[float] = None) -> None:
        if isinstance(data, Mapping):
            data = data.items()
        for (key, value) in data:
            self.put(key, value, max_age)

    def get_many(self, keys: Iterable[Any],
                 default: Any = ...) -> List[Tuple[Any, Any]]:
        data = []
        for key in keys:
            try:
                value = self.get(key)
            except KeyError:
                if default is Ellipsis:
                    continue
                value = default
            data.append((key, value))
        return data

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
