import importlib
from pathlib import Path
from typing import Union, Optional, Any

import pluca


def create_cachedir_tag(cache_dir: Union[str, Path],
                        name: Optional[str] = 'pluca cache',
                        force: bool = False) -> None:
    if isinstance(cache_dir, str):
        cache_dir = Path(cache_dir)

    try:
        with open(cache_dir / 'CACHEDIR.TAG',
                  'w' if force else 'x',
                  encoding='utf-8') as fd:
            fd.write('Signature: 8a477f597d28d172789f06886806bc55\n'
                     '# This file is a cache directory tag '
                     f'created by {name}.')
    except FileExistsError:
        pass


def create_cache(cls: str, **kwargs: Any) -> pluca.Cache:
    (module, class_) = cls.rsplit('.', 1)
    mod = importlib.import_module(module)
    factory = getattr(mod, class_)
    if not callable(factory):
        raise AttributeError(f'{cls} is not callable')
    cache = factory(**kwargs)
    if not isinstance(cache, pluca.Cache):
        raise TypeError('f{cls} is not a cache factory')
    return cache
