import logging
from collections.abc import Mapping
from typing import Any

from pluca import Cache
from .utils import create_cache

_caches: dict[tuple[str, ...], Cache] = {}

_nodes: dict[tuple[str, str], Cache] = {}

logger = logging.getLogger(__name__)

_DEFAULT_BACKEND = 'file'


def add(node: str | None, cls: str, reuse: bool = True,
        **kwargs: Any) -> None:

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
        cache = create_cache(cls, **kwargs)

    if node and ('',) not in _caches:
        # No root cache.
        basic_config()

    _nodes[node_key] = cache
    _caches[tnode] = cache

    logger.debug('Set up %r %s', cache,
                 f'for {node!r}' if node else 'as root cache')


def get_cache(node: str | None = None) -> Cache:
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
    return get_cache(f'{parent or ""}.{child}')


def remove(node: str | None = None, shutdown: bool = True) -> None:
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
    if shutdown:
        for cache in _caches.values():
            cache.shutdown()
    _caches.clear()
    _nodes.clear()
    logger.debug('All caches removed')


def flush() -> None:
    for cache in _caches.values():
        cache.flush()


def gc() -> None:
    for cache in _caches.values():
        try:
            cache.gc()
        except NotImplementedError:
            pass


def basic_config(cls: str = _DEFAULT_BACKEND, **kwargs: Any) -> None:
    remove_all()
    add('', cls=cls, **kwargs)


def dict_config(config: Mapping[str, Any]) -> None:
    config = dict(config)

    caches = config.pop('caches', {})

    remove_all()

    cls = config.pop('class', _DEFAULT_BACKEND)
    add('', cls=cls, **config)

    for node, cfg in caches.items():
        cfg = dict(cfg)
        cls = cfg.pop('class', _DEFAULT_BACKEND)
        add(node, cls=cls, **cfg)


def file_config(filename: str, encoding: str | None = None) -> None:
    import configparser  # pylint: disable=import-outside-toplevel

    config = configparser.ConfigParser()
    config.read(filename, encoding=encoding)

    remove_all()

    try:
        section = dict(config['__root__'])
    except KeyError:
        section = {}

    cls = section.pop('class', _DEFAULT_BACKEND)
    add('', cls=cls, reuse=False, **section)

    for name in filter(lambda x: x != '__root__', config.sections()):
        cfg: dict[str, Any] = dict(config[name])
        cls = cfg.pop('class', _DEFAULT_BACKEND)
        add(name, cls=cls, **cfg)
