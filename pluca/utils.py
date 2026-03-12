import importlib
from pathlib import Path
from typing import Any

import pluca


def _is_module_allowed(module: str, allowed_modules: tuple[str, ...]) -> bool:
    for prefix in allowed_modules:
        if module == prefix or module.startswith(f'{prefix}.'):
            return True
    return False


def create_cachedir_tag(cache_dir: str | Path,
                        name: str | None = 'pluca cache',
                        force: bool = False) -> None:
    """Create a ``CACHEDIR.TAG`` marker file.

    Args:
        cache_dir: Cache directory path.
        name: Generator name written in the tag comment.
        force: Overwrite an existing tag when ``True``.

    """
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


def create_cache(cls: str,
                 allowed_modules: tuple[str, ...] | None = None,
                 **kwargs: Any) -> pluca.Cache:
    """Instantiate a cache object from a dotted factory path.

    Args:
        cls: Dotted import path to a cache factory.
        allowed_modules: Optional tuple of allowed module prefixes for
            ``cls``. When provided, ``cls`` must resolve to one of those
            modules or their submodules.
        **kwargs: Named arguments passed to the factory.

    Returns:
        The cache instance produced by the factory.

    Raises:
        AttributeError: If the resolved attribute is not callable.
        ValueError: If ``allowed_modules`` is empty or ``cls`` is outside the
            configured module allowlist.
        TypeError: If the factory result is not a ``pluca.Cache``.

    """
    (module, class_) = cls.rsplit('.', 1)
    if allowed_modules is not None:
        if not allowed_modules:
            raise ValueError('allowed_modules cannot be empty')
        if not _is_module_allowed(module, allowed_modules):
            raise ValueError(
                f'{cls!r} is not allowed; module must match one of '
                f'{allowed_modules!r}')
    mod = importlib.import_module(module)
    factory = getattr(mod, class_)
    if not callable(factory):
        raise AttributeError(f'{cls} is not callable')
    cache = factory(**kwargs)
    if not isinstance(cache, pluca.Cache):
        raise TypeError('f{cls} is not a cache factory')
    return cache
