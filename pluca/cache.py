import logging
from collections.abc import Mapping
from typing import Any

from pluca import Cache
from .utils import create_cache

_caches: dict[tuple[str, ...], Cache] = {}

_nodes: dict[tuple[str, str], Cache] = {}

logger = logging.getLogger(__name__)

_DEFAULT_BACKEND = 'file'


def _coerce_file_config_value(value: str) -> Any:
    value_l = value.lower()

    if value_l == 'true':
        return True
    if value_l == 'false':
        return False

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        return value


def _coerce_file_config_section(
        section: Mapping[str, str]) -> dict[str, Any]:
    return {name: _coerce_file_config_value(value)
            for (name, value) in section.items()}


def add(node: str | None, cls: str, reuse: bool = True,
        allowed_class_modules: tuple[str, ...] | None = None,
        **kwargs: Any) -> None:
    """Register a cache backend for a node.

    Args:
        node: Dot-delimited cache node path. ``None`` targets the root node.
        cls: Fully qualified cache factory path. Short names are resolved as
            ``pluca.<name>.Cache``.
        reuse: Reuse an existing cache instance with identical class and
            arguments when available.
        allowed_class_modules: Optional tuple of allowed module prefixes used
            to validate ``cls`` before importing.
        **kwargs: Named arguments passed to the cache factory.

    Raises:
        ValueError: If the node is already configured.

    """

    if node is None:
        node = ''

    tnode = tuple(node.split('.'))
    if tnode in _caches:
        raise ValueError(f'A cache named {node!r} already exists')

    if '.' not in cls:
        cls = f'pluca.{cls}.Cache'

    node_key = (cls, repr(tuple(kwargs.items())))

    cache: Cache | None = _nodes.get(node_key, None) if reuse else None

    if not cache:
        cache = create_cache(cls,
                             allowed_modules=allowed_class_modules,
                             **kwargs)

    if node and ('',) not in _caches:
        # No root cache.
        basic_config()

    _nodes[node_key] = cache
    _caches[tnode] = cache

    logger.debug('Set up %r %s', cache,
                 f'for {node!r}' if node else 'as root cache')


def get_cache(node: str | None = None) -> Cache:
    """Get the cache configured for a node.

    The lookup falls back through parent nodes until the root cache.

    Args:
        node: Dot-delimited node path. ``None`` targets the root lookup.

    Returns:
        The resolved cache instance.

    """
    if node is None:
        node = ''

    if not _caches:
        basic_config()

    tnode = tuple(node.split('.'))
    nr = len(tnode)

    while nr:
        try:
            return _caches[tnode[:nr]]
        except KeyError:
            pass
        nr -= 1

    return _caches[('',)]


def get_child(parent: str | None, child: str) -> Cache:
    """Get a child node cache.

    Args:
        parent: Parent node path.
        child: Child node name.

    Returns:
        The cache resolved for ``parent.child``.

    """
    return get_cache(f'{parent or ""}.{child}')


def remove(node: str | None = None, shutdown: bool = True) -> None:
    """Remove a configured node cache.

    Args:
        node: Dot-delimited node path. ``None`` targets the root node.
        shutdown: Call ``shutdown()`` on the cache before removing it.

    Raises:
        KeyError: If the node does not exist and it is not the root.

    """
    if node is None:
        node = ''

    tnode = tuple(node.split('.'))

    try:
        cache = _caches[tnode]
    except KeyError as ex:
        if not node:
            return
        raise KeyError(node) from ex

    if shutdown:
        cache.shutdown()

    del _caches[tnode]

    logger.debug('Removed cache for %r', node)


def remove_all(shutdown: bool = True) -> None:
    """Remove all configured caches.

    Args:
        shutdown: Call ``shutdown()`` on each cache before clearing.

    """
    if shutdown:
        for cache in _caches.values():
            cache.shutdown()
    _caches.clear()
    _nodes.clear()
    logger.debug('All caches removed')


def flush() -> None:
    """Flush all configured caches."""
    for cache in _caches.values():
        cache.flush()


def gc() -> None:
    """Run garbage collection on all configured caches.

    Backends that do not support garbage collection are skipped.

    """
    for cache in _caches.values():
        try:
            cache.gc()
        except NotImplementedError:
            pass


def basic_config(cls: str = _DEFAULT_BACKEND,
                 allowed_class_modules: tuple[str, ...] | None = None,
                 **kwargs: Any) -> None:
    """Configure only the root cache.

    Args:
        cls: Cache factory path or short backend name.
        allowed_class_modules: Optional tuple of allowed module prefixes used
            to validate ``cls`` before importing.
        **kwargs: Named arguments passed to the cache factory.

    """
    remove_all()
    add('', cls=cls,
        allowed_class_modules=allowed_class_modules,
        **kwargs)


def dict_config(config: Mapping[str, Any],
                allowed_class_modules: tuple[str, ...] | None = None) -> None:
    """Configure cache nodes from a mapping.

    Args:
        config: Mapping with root cache options and optional ``caches`` child
            mapping where each key is a node name.
        allowed_class_modules: Optional tuple of allowed module prefixes used
            to validate configured ``class`` paths before importing.

    """
    config = dict(config)

    caches = config.pop('caches', {})

    remove_all()

    cls = config.pop('class', _DEFAULT_BACKEND)
    add('', cls=cls,
        allowed_class_modules=allowed_class_modules,
        **config)

    for node, cfg in caches.items():
        cfg = dict(cfg)
        cls = cfg.pop('class', _DEFAULT_BACKEND)
        add(node, cls=cls,
            allowed_class_modules=allowed_class_modules,
            **cfg)


def file_config(filename: str,
                encoding: str | None = None,
                allowed_class_modules: tuple[str, ...] | None = None) -> None:
    """Configure cache nodes from an INI-style file.

    Args:
        filename: Configuration file path.
        encoding: Optional file encoding.
        allowed_class_modules: Optional tuple of allowed module prefixes used
            to validate configured ``class`` paths before importing.

    """
    import configparser  # pylint: disable=import-outside-toplevel

    config = configparser.ConfigParser()
    config.read(filename, encoding=encoding)

    remove_all()

    try:
        section = dict(config['__root__'])
    except KeyError:
        section = {}

    cls = section.pop('class', _DEFAULT_BACKEND)
    add('', cls=cls, reuse=False,
        allowed_class_modules=allowed_class_modules,
        **_coerce_file_config_section(section))

    for name in filter(lambda x: x != '__root__', config.sections()):
        cfg = dict(config[name])
        cls = cfg.pop('class', _DEFAULT_BACKEND)
        add(name, cls=cls,
            allowed_class_modules=allowed_class_modules,
            **_coerce_file_config_section(cfg))
