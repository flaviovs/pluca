
import argparse
import dbm.dumb
import gc
import os
import random
import string
import sys
import time
import tempfile
from typing import Any, NamedTuple
from collections.abc import Callable

import pluca
import pluca.file
import pluca.memory
import pluca.null
import pluca.sqlite3
import pluca.dbm


class _ATuple(NamedTuple):
    attr1: str
    attr2: float


class _Random(random.Random):

    def __init__(self) -> None:
        super().__init__(12345)  # NB: fixed seed.

    def random_string(self) -> str:
        return ''.join(self.choice(string.ascii_letters) for i in range(50))

    def random_tuple(self) -> tuple[Any, ...]:
        data = [
            self.randint(-1_000_000, 1_000_000),
            self.random_string(),
            _ATuple(attr1=self.random_string(), attr2=self.random()),
            self.random(),
            True,
            False,
        ]
        self.shuffle(data)
        return tuple(data)


def _get_data(nr: int) -> list[tuple[tuple[Any, ...], tuple[Any, ...]]]:
    data = []
    prng = _Random()
    for _ in range(nr):
        data.append((prng.random_tuple(), prng.random_tuple()))
    return data


def print_header(entries: int) -> None:
    unm = os.uname()
    # pylint: disable-next=[bad-builtin]
    print(f'''
Benchmarking with Python {sys.version} ({sys.implementation.name}) on
{unm.sysname} {unm.release} {unm.machine} with {entries:,} cache entries.
                            put()         get()      put()+get()    get() 50%
Cache                   secs     op/s secs     op/s secs     op/s secs     op/s
----------------------- ------------- ------------- ------------- -------------
''', end='')


# pylint: disable-next=too-many-locals
def benchmark(name: str, entries: int,
              adapter_factory: Callable[..., Any], **kwargs: Any) -> None:
    prng = _Random()

    data = _get_data(entries)
    miss_data = _get_data(entries)

    prng = _Random()

    gc_enabled = gc.isenabled()

    gc.disable()

    gc.collect()
    cache = pluca.Cache(adapter_factory(**kwargs))
    put_start = time.time()
    for key, value in data:
        cache.put(key, value)
    put_end = time.time()

    get_start = time.time()
    for key, value in data:
        cache.get(key, value)
    get_end = time.time()

    get_miss_start = time.time()
    for key, value in miss_data:
        cache.get(key, value)
    get_miss_end = time.time()

    cache.flush()
    del cache
    gc.collect()

    exp = [(0 if prng.random() > 0.5 else None) for _ in range(entries)]
    cache = pluca.Cache(adapter_factory(**kwargs))
    get_mixed_start = time.time()
    for i, (key, value) in enumerate(data):
        cache.put(key, value, exp[i])
        cache.get(key, value)
    get_mixed_end = time.time()

    if gc_enabled:
        gc.enable()

    cache.shutdown()

    put_duration = put_end - put_start
    get_duration = get_end - get_start
    get_miss_duration = get_miss_end - get_miss_start
    get_mixed_duration = get_mixed_end - get_mixed_start

    # pylint: disable-next=[bad-builtin]
    print(f'{name:22.22} '
          f'{put_duration:4.1f} {entries / put_duration:9,.1f}'
          f'{get_duration:4.1f} {entries / get_duration:9,.1f}'
          f'{get_miss_duration:4.1f} {entries / get_miss_duration:9,.1f}'
          f'{get_mixed_duration:4.1f} {entries / get_mixed_duration:9,.1f}'
          )

    gc.collect()


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--entries',
                        type=int,
                        help='Cache entries to test (default: %(default)d)',
                        default=10_000)
    args = parser.parse_args()

    print_header(args.entries)

    benchmark('File lock=None', args.entries, pluca.file.Adapter,
              locking=None)

    if os.name != 'nt':
        benchmark('File lock=flock', args.entries,
                  pluca.file.Adapter, locking='flock')

    if os.name == 'nt':
        benchmark('File lock=msvcrt', args.entries,
                  pluca.file.Adapter, locking='msvcrt')

    benchmark('File lock=mkdir', args.entries,
              pluca.file.Adapter, locking='mkdir')

    benchmark('Memory unbounded', args.entries, pluca.memory.Adapter)
    benchmark(f'Memory {args.entries // 2:,}',
              args.entries, pluca.memory.Adapter,
              max_entries=args.entries // 2)
    benchmark(f'Memory {args.entries // 2:,} prune=20%',
              args.entries, pluca.memory.Adapter,
              max_entries=args.entries // 2,
              prune=int(args.entries * 0.2))
    benchmark('Null', args.entries, pluca.null.Adapter)

    with tempfile.NamedTemporaryFile() as ctx:
        benchmark('SQLite file',
                  args.entries, pluca.sqlite3.Adapter, filename=ctx.name)

    with tempfile.NamedTemporaryFile() as ctx:
        benchmark('SQLite file autocommit',
                  args.entries, pluca.sqlite3.Adapter,
                  filename=ctx.name, isolation_level=None)

    with tempfile.NamedTemporaryFile() as ctx:
        benchmark('SQLite file WAL',
                  args.entries, pluca.sqlite3.Adapter,
                  filename=ctx.name, pragma={'journal_mode': 'WAL'})

    benchmark('SQLite :memory:',
              args.entries, pluca.sqlite3.Adapter, filename=':memory:')

    with tempfile.TemporaryDirectory() as tempdir:
        dbd = dbm.dumb.open(f'{tempdir}/db', 'n')
        benchmark('DBM dumb', args.entries, pluca.dbm.Adapter, db=dbd)
        dbd.close()


if __name__ == '__main__':
    _main()
