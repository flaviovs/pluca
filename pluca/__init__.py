import abc
from typing import Optional, Any, Iterable, Mapping, Callable, NoReturn, Dict


class Cache(abc.ABC):

    _pickle = None
    _hash_algo = None

    def _init_hash_algo(self):
        import hashlib
        self._hash_algo = hashlib.md5

    def _init_pickle(self):
        import pickle
        self._pickle = pickle

    def __getstate__(self) -> Dict[str, Any]:
        self.__dict__['_pickle'] = self.__dict__['_hash_algo'] = None
        return self.__dict__

    def _get_key_hash(self, key: Any) -> str:
        if not self._hash_algo:
            self._init_hash_algo()
        assert self._hash_algo is not None
        algo = self._hash_algo()
        algo.update(str(key).encode('utf-8'))
        return algo.hexdigest()

    @abc.abstractclassmethod
    def _put(self, key: Any, value: Any, max_age: Optional[float] = None):
        pass

    @abc.abstractclassmethod
    def _get(self, key) -> Any:
        pass

    @abc.abstractclassmethod
    def _touch(self, key) -> None:
        pass

    @abc.abstractclassmethod
    def _flush(self) -> None:
        pass

    def has(self, key: Any) -> bool:
        try:
            self.get(key)
            return True
        except KeyError:
            return False

    def flush(self):
        self._flush()

    def touch(self, key: Any) -> None:
        self._touch(key)

    def put(self, key: Any, value: Any,
            max_age: Optional[float] = None) -> None:
        if not self._pickle:
            self._init_pickle()
        self._put(key, value, max_age)

    def get(self, key: Any, default: Any = None) -> Any:
        if not self._pickle:
            self._init_pickle()

        try:
            return self._get(key)
        except KeyError:
            if default is not None:
                return default
            raise

    def get_put(self, key: Any, func: Callable[[], Any],
                max_age: Optional[float] = None) -> Any:
        try:
            return self.get(key)
        except KeyError:
            pass
        value = func()
        self.put(key, value, max_age)
        return value

    def put_many(self, values: Mapping[Any, Any], max_age) -> None:
        for (k, v) in values.items():
            self.put(k, v)

    def get_many(self, keys: Iterable[Any],
                 default: Any = None) -> Mapping[Any, Any]:
        return {k: self.get(k, default) for k in keys}

    def gc(self) -> Optional[NoReturn]:
        raise NotImplementedError(f'{self.__class__.__qualname__} does not '
                                  'support garbage collection')
