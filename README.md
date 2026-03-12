Pluggable caching for Python
============================

*pluca* is a Python caching library for applications and libraries that
need a consistent cache API across different storage backends. It
includes file-based, SQLite, in-memory, and other cache backends that
can be swapped with minimal code changes.

The name *pluca* stands for "pluggable cache architecture". The project
is built around the idea that application code should be able to depend
on one cache interface while choosing the storage backend that best fits
each use case.

Supported Python versions: 3.11+.

Why pluca
---------
- Unified cache interface for multiple backends
- Built-in file, SQLite, and memory caches
- Decorator support for caching function return values
- No external runtime dependencies

Features
--------
- Unified cache interface - your application can just instantiate a
  `Cache` object and pass it around — client code just accesses the
  cache without having to know any of the back-end details,
  expiration logic, etc.
- Easy interface - writing a *pluca* cache for a new backend
  is very straightforward
- It is fast - the library is developed with performance in mind
- It works out-of-box - a file system cache is provided that can be
  used out-of-box
- No batteries needed - *pluca* has no external dependencies

File backend
------------

The `pluca.file` backend stores cache entries on the file system while
keeping the same cache API used by the other backends.

    >>> import pluca.file
    >>> file_cache = pluca.file.Cache(name='docs-file-cache')
    >>> file_cache.put('answer', 42)
    >>> file_cache.get('answer')
    42

This backend works well when you want a disk-backed cache for CLI
tools, desktop applications, background jobs, or other programs that
need cached values to remain available between runs.

SQLite backend
--------------

The `pluca.sqlite3` backend stores cache entries in a SQLite database
while preserving the same pluggable cache interface.

    >>> import pluca.sqlite3
    >>> import tempfile
    >>> sqlite_tempdir = tempfile.TemporaryDirectory()
    >>> sqlite_cache = pluca.sqlite3.Cache(
    ...     filename=f'{sqlite_tempdir.name}/cache.db')
    >>> sqlite_cache.put('user-count', 123)
    >>> sqlite_cache.get('user-count')
    123

This backend is useful when you want a persistent local cache with a
single-file database and atomic bulk writes via `put_many()`.

Memory backend
--------------

The `pluca.memory` backend keeps cached values in process memory for
fast repeated lookups during the life of the cache object.

    >>> import pluca.memory
    >>> memory_cache = pluca.memory.Cache(max_entries=1000)
    >>> memory_cache.put('greeting', 'hello')
    >>> memory_cache.get('greeting')
    'hello'

This backend is a good fit for temporary application caching, repeated
function results, and other cases where in-memory speed matters more
than persistence.

It also supports automatic maximum entry control so a cache can cap its
size instead of growing until it fills all available memory.

The full list of built-in backends is available in the
**Included backends** section below.

Use cases
---------
- Add Python caching to an application without coupling code to one
  storage engine
- Use a file-backed cache for local persistent caching
- Use SQLite for persistent cache storage in a single database file
- Use an in-memory cache for fast in-process lookups
- Swap cache backends without changing application cache logic
- Cache expensive calculations or function return values

How to use
----------

First import the cache module:

    >>> import pluca.file  # Use a file system cache.

Now create the cache object:

    >>> cache = pluca.file.Cache()

Store _3.1415_ in the cache using _pi_ as key:

    >>> cache.put('pi', 3.1415)

Now retrieve the value from the cache.

    >>> pi = cache.get('pi')
    >>> pi
    3.1415
    >>> type(pi)
    <class 'float'>

Non-existent or expired cache entries raise `KeyError`.

    >>> cache.get('notthere')
    Traceback (most recent call last):
        ...
    KeyError: 'notthere'

Use `remove()` to delete entries from the cache:

    >>> cache.put('foo', 'bar')
    >>> cache.get('foo')
    'bar'
    >>> cache.remove('foo')
    >>> cache.get('foo')
    Traceback (most recent call last):
        ...
    KeyError: 'foo'

On composite caches, `remove()` attempts removal on every configured
child cache and raises `KeyError` only when the key is missing from all
tiers.

To test if an entry exists, use `has()`:

    >>> cache.put('this', 'is in the cache')
    >>> cache.has('this')
    True
    >>> cache.has('that')
    False

You can provide a default value for when the key does not exist or has
expired. The method will not raise _KeyError_ in this case, it will
return the default value instead.

    >>> cache.get('notthere', 12345)
    12345

By default cache entries are set to “never” expire — cache adapters
can expire entries though, for example to use less resource. Here’s an
example of how to store a cache entry with an explicit expiration
time:

    >>> cache.put('see-you', 'in two secs', 1)  # Expire in 1 second.
    >>> import time; time.sleep(1)  # Wait for it to expire.
    >>> cache.get('see-you')
    Traceback (most recent call last):
        ...
    KeyError: 'see-you'

Passing `max_age=0` marks an entry as immediately expired, while
`max_age=None` keeps the default behavior (no explicit expiration).

Cache keys can be any object (but see _Caveats_ below):

    >>> key = (__name__, True, 'this', 'key', 'has', 'more', 'than', 1, 'value')
    >>> cache.put(key, 'data')
    >>> cache.get(key)
    'data'

Cached values can be any pickable data:

    >>> import datetime
    >>> alongtimeago = datetime.date(2020, 1, 1)
    >>> cache.put('alongtimeago', alongtimeago)
    >>> today = cache.get('alongtimeago')
    >>> today
    datetime.date(2020, 1, 1)
    >>> type(today)
    <class 'datetime.date'>

Flushing the cache removes all entries:

    >>> cache.put('bye', 'tchau')
    >>> cache.flush()
    >>> cache.get('bye')
    Traceback (most recent call last):
        ...
    KeyError: 'bye'

Calling `flush()` on a fresh cache with no stored entries is safe and
acts as a no-op.

## Abstracting cache backends

Here’s how to abstract cache backends. First, let’s define a function
that calculates a factorial. The function also receives a cache object
to store results, so that the calculation results are cached.

    >>> from math import factorial
    >>> def cached_factorial(cache, n):
    ...     try:
    ...         res = cache.get(('factorial', n))
    ...     except KeyError:
    ...         print(f'CACHE MISS - calculating {n}!')
    ...         res = factorial(n)
    ...         cache.put(('factorial', n), res)
    ...     return res

Now let’s try this with the file cache created above. First call
should be a cache miss:

    >>> cached_factorial(cache, 10)
    CACHE MISS - calculating 10!
    3628800

Subsequent calls should get the results from the cache:

    >>> cached_factorial(cache, 10)
    3628800

Now let's switch to the “null” backend (the “null” backend does not
store the data anywhere — see `help(pluca.null.Cache)` for more info):

    >>> import pluca.null
    >>> null_cache = pluca.null.Cache()
    >>>
    >>> cached_factorial(null_cache, 10)
    CACHE MISS - calculating 10!
    3628800


## Using caches as decorators

Caches can also be used as decorator to cache function return values:

    >>> @cache
    ... def expensive_calculation(alpha, beta):
    ...     res = 0
    ...     print('Doing expensive calculation')
    ...     for i in range(0, alpha):
    ...         for j in range(0, beta):
    ...             res = i * j
    ...     return res
    >>>
    >>> cache.flush()  # Let's start with an empty cache.
    >>>
    >>> expensive_calculation(10, 20)
    Doing expensive calculation
    171

Calling the function again with the same parameters returns the cached
result:

    >>> expensive_calculation(10, 20)
    171

Each function can have their own expiration:

    >>> @cache(max_age=1)  # Expire after one second.
    ... def quick_calculation(alpha, beta):
    ...     print(f'Calculating {alpha} + {beta}')
    ...     return alpha + beta

First call executes the function. Second call gets the cached value.

    >>> quick_calculation(1, 2)
    Calculating 1 + 2
    3
    >>> quick_calculation(1, 2)
    3

After the expiry time the calculation is done again:

    >>> import time; time.sleep(1)
    >>> quick_calculation(1, 2)
    Calculating 1 + 2
    3


## Miscellaneous cache methods

Use `get_put()` to conveniently get a value from the cache, or call a
function to generate it, if it is not cached already:

    >>> cache.flush()
    >>>
    >>> def calculate_foo():
    ...    print('Calculating foo')
    ...    return 'bar'
    >>>
    >>> cache.get_put('foo', calculate_foo)
    Calculating foo
    'bar'

    >>> cache.get_put('foo', calculate_foo)
    'bar'

You can add many entries to the cache at once by calling
`put_many()`:

    >>> cache.put_many({'foo': 'bar', 'zee': 'too'})
    >>> cache.get('zee')
    'too'

You can also pass an iterable of _(key, value)_ tuples. This is
useful for caching with non-hashable keys:

    >>> cache.put_many([(['a', 'b', 'c'], 123), ('pi', 3.1415)])
    >>> cache.get(['a', 'b', 'c'])
    123

On the `sqlite3` backend, `put_many()` is atomic: all rows are written
in a single transaction and committed once. If one row fails, no rows
from that `put_many()` call are persisted.

New `sqlite3` cache tables are created with SQLite `WITHOUT ROWID`.

Use `get_many()` to get many results at once. This method returns a
list of _(key, value)_ tuples:

    >>> cache.get_many(['zee', 'pi'])
    [('zee', 'too'), ('pi', 3.1415)]

Notice that `get_many()` does **not** raise _KeyError_ when a key is
not found or has expired. Instead, the key will not be present in the
returned list:

    >>> cache.get_many(['pi', 'not-there'])
    [('pi', 3.1415)]

However, you can pass a default value to `get_many()`. This value will
be returned for any non-existing keys:

    >>> cache.get_many(['pi', 'not-there', 'also-not-there'], default='yes')
    [('pi', 3.1415), ('not-there', 'yes'), ('also-not-there', 'yes')]

Use `remove_many()` to remove multiple keys at once. Missing keys are
ignored:

    >>> cache.put_many({'x': 1, 'y': 2})
    >>> cache.remove_many(['x', 'not-there'])
    >>> cache.get('x')
    Traceback (most recent call last):
        ...
    KeyError: 'x'
    >>> cache.get('y')
    2


## Garbage collection.

Garbage collection tells the cache to remove expired entries to save
resources. This is done by the `gc()` method:

    >>> cache.gc()

Notice that **pluca never calls `gc()` automatically** — it is up to
your application to call it eventually to do garbage collection.

Calling `gc()` on a fresh cache is also safe and behaves as a no-op.


Global Cache API
----------------

_pluca_ comes with a separate cache API that allows libraries and
applications to benefit from caching in a very flexible way. On one
hand, it allows libraries that would benefit from caching to use
_pluca_ even if the calling application doesn’t support it. On the
other hand, an application that does support _pluca_ can customize
caches for specific libraries without any extra API.

In the sections below you will see how the Global Cache API works both
from a library and an application perspective, but before that it is
important to understand how this API organizes cache objects.


## The cache object tree

Cache objects are organized in a tree structure. Nodes are positioned
in this tree by using “.” (dot) separated names. The “” (the empty
string) node is special, and points to the root node.

When looking up a cache object by name, the API will first look for
the exact node name. If none is found, then it will “move up” the tree
and check for common parents. It will do this until it finds a
matching cache name. If none is found, the root cache is returned.

The _pluca_ Global Cache API hierarchy is pretty much identical to the
way [Python’s logging
facility](https://docs.python.org/3/library/logging.html) organizes
loggers.

As a quick example, let’s say you configure three cache objects:

- The root cache is a file cache
- “pkg“ is a memory cache
- “pkg.mod“ is a null cache

Then a lookup of “pkg.mod” would return the null cache. If you look
up “pkg.foobar”, then the memory cache would be returned, because
although there’s no cache at “pkg.foobar”, they share the common
prefix “pkg“. Lastly, if you look up “another.module” then you’ll get
the root cache, because neither the name nor any of its ancestors
exist on the cache tree.


## Using the Global Cache API in libraries

Let’s say your library has a module file called `mymodule.py`, and this
module has some functions that would greatly benefit from caching.

Hard-coding _pluca_ cache instances inside your library may not be a
good idea. You could design some API or configuration system to allow
your library to use application-provided caches, but this would make
things more complex, both for you and application developers.

The Global Cache API makes this very simple. In your library, all you
need to do is this:

    >>> import pluca.cache
    >>>
    >>> cache = pluca.cache.get_cache(__name__)

That’s it. `cache` is a ready-to-use _pluca_ cache object:

    >>> result = cache.get('my-very-expensive-calculation', None)

Notice that in this example we ask for a cache named `__name__`, which
is the absolute name of your module or package. By matching modules
and packages hierarchically, the API allows for fine-grained cache
configuration without any coupling between applications and libraries.


## Using the Global Cache API in an application

The quickest way to configure the API for the most common use case of
a single application using a single cache is to call
`pluca.cache.basic_config()`:

    >>> pluca.cache.basic_config()

This sets up a file cache as the root cache. If desired, you can use
another backend:

    >>> # Configure a memory cache as the cache root.
    >>> pluca.cache.basic_config('pluca.memory')

You can also customize the cache object:

    >>> pluca.cache.basic_config('pluca.file', cache_dir='/tmp')

To disable file locking for a file backend instance:

    >>> pluca.cache.basic_config('pluca.file', cache_dir='/tmp', locking=None)

**Note**: when you call `basic_config()` all existing caches are
removed before the new one is set up.

To configure additional caches, use `pluca.cache.add()`:

    >>> pluca.cache.add('mod', 'pluca.memory', max_entries=100)
    >>> pluca.cache.add('pkg.foo', 'pluca.null')

This adds two caches — one at “mod“ and another at “pkg.foo“. Now, in
the “pkg.foo“ module, the call `get_cache(__name__)` will return a
“null” cache, whereas the same call on the “mod“ module will return a
memory cache.

    >>> # In mod.py
    >>> cache = pluca.cache.get_cache(__name__)
    >>> cache  # doctest: +SKIP
    MemoryCache(max_entries=None)

Calling `get_cache()` returns the root cache:

    >>> cache = pluca.cache.get_cache()
    >>> cache  # doctest: +ELLIPSIS
    FileCache(name=..., cache_dir=...)

To resolve a direct child cache from a parent node, use `get_child()`:

    >>> pluca.cache.get_child('pkg', 'mod') is pluca.cache.get_cache('pkg.mod')
    True

If the parent is `None` or an empty string, `get_child()` resolves the
same node as `get_cache(child)`:

    >>> pluca.cache.get_child(None, 'mod') is pluca.cache.get_cache('mod')
    True


A call from another random module would return the root (file) cache:

    >>> # In another.py
    >>> cache = pluca.cache.get_cache(__name__)
    >>> cache  # doctest: +ELLIPSIS
    FileCache(name=..., cache_dir=...)

**NOTE**: a root cache is always required. If you don’t set up the root
cache, then `pluca.cache.basic_config()` will be called to set up one
for you.

The function `add()` has the following signature:

```python
add(node: str | None, factory: str, reuse: bool = True,
    allowed_class_modules: tuple[str, ...] | None = None, **kwargs: Any)
```

Here, `node` is the cache node name. Pass `None` to configure the root
node explicitly. `factory` indicates the cache factory you want to use for
that node.

The `factory` parameter can be a fully-qualified module path (for example,
`mycustomcache`). Cache factories are resolved using the
`pkg.module:Factory` format. If `:Factory` is omitted, `:Cache` is
assumed. So `mycustomcache` means `mycustomcache:Cache`.

Repository examples intentionally omit `:Cache` and use module paths
directly.

Factory paths are dynamic imports and should be treated as trusted input
only. Do not load cache factory names from untrusted configuration unless
you also enforce an allowlist with `allowed_class_modules`.

By default, caches will reuse previously created instances with the
same `factory` and arguments. For example, the two `get_cache()`
calls below return the same cache object:

    >>> pluca.cache.add('c1', 'pluca.file')
    >>> pluca.cache.add('c2', 'pluca.file')
    >>> pluca.cache.get_cache('c1') is pluca.cache.get_cache('c2')
    True

To prevent this from happening, pass _False_ on the `reuse` parameter:

    >>> pluca.cache.add('c3', 'pluca.file', reuse=False)
    >>> pluca.cache.get_cache('c2') is pluca.cache.get_cache('c3')
    False

The remaining arguments to the `add()` function are passed unchanged
to the cache factory.

To restrict dynamic class loading, pass `allowed_class_modules`. This
accepts module prefixes, so `('pluca',)` allows classes under
`pluca.*`:

    >>> pluca.cache.add('safe', 'pluca.memory',
    ...                 allowed_class_modules=('pluca',))

For `pluca.file.Cache`, the `name` argument is treated as a cache
identifier, not a path. It must be a single safe path segment (for
example `mycache`): it cannot be absolute, cannot contain `/` or `\\`,
and cannot be `.` or `..`.

    >>> pluca.cache.add('c4', 'pluca.file', name='c4', cache_dir='/tmp')
    >>> pluca.cache.get_cache('c4')  # doctest: +ELLIPSIS
    FileCache(name='c4', cache_dir=PosixPath('/tmp'), locking=...)

You can also explicitly choose locking behavior per file cache:

    >>> pluca.cache.add('c4.nolock', 'pluca.file', name='c4_nolock',
    ...                 cache_dir='/tmp', locking=None)

You can also configure the API using a dict-like object using
`pluca.cache.dict_config()`:

    >>> pluca.cache.dict_config({
    ...     'factory': 'pluca.memory',  # The root cache.
    ...     'max_entries': 10,
    ...
    ...     'caches': {  # Configure extra caches.
    ...         'mod': {
    ...             'factory': 'pluca.null',
    ...         },
    ...         'pkg.mod': {
    ...             'factory': 'pluca.file',
    ...             'name': 'pkg_mod',
    ...             'cache_dir': '/tmp',
    ...         },
    ...     },
    ... })
    >>> pluca.cache.get_cache('mod')
    NullCache()

To restrict dynamic class loading, pass `allowed_class_modules`. This
accepts module prefixes, so `('pluca',)` allows classes under
`pluca.*`:

    >>> pluca.cache.dict_config({
    ...     'factory': 'pluca.memory',
    ... }, allowed_class_modules=('pluca',))

Values loaded from INI files are parsed conservatively before they are
passed to cache constructors: `true`/`false` become booleans, integer
and floating-point literals become numbers, and any other value is kept
as a string.

A facility to set up the API using a configuration file is also
provided. Here is an example:

    >>> from tempfile import NamedTemporaryFile
    >>>
    >>> temp = NamedTemporaryFile(mode='w+', suffix='.ini')
    >>> n = temp.write('''
    ...
    ...     [__root__]
    ...     factory = pluca.memory
    ...     max_entries = 10
    ...
    ...     [mod]
    ...     factory = pluca.null
    ...
    ...     [pkg.mod]
    ...     factory = pluca.file
    ...     name = pkg_mod
    ...     cache_dir = /tmp
    ...
    ... ''')
    >>> temp.flush()
    >>>
    >>> pluca.cache.file_config(temp.name)
    >>>
    >>> pluca.cache.get_cache('mod')
    NullCache()

The same restriction is available for INI-based configuration:

    >>> pluca.cache.file_config(temp.name,
    ...                         allowed_class_modules=('pluca',))


### Removing caches

To remove a configured cache node, call `pluca.cache.remove()`:

    >>> pluca.cache.remove('mod')

Notice that removing a node does not remove its children:

    >>> pluca.cache.add('a.b', 'pluca.file')
    >>> pluca.cache.add('a.b.c', 'pluca.file')
    >>> pluca.cache.remove('a.b')
    >>> pluca.cache.get_cache('a.b.c')  # doctest: +ELLIPSIS
    FileCache(name=...)

To remove all configured cache nodes and effectively reset the Global
Cache API, call `pluca.cache.remove_all()`:

    >>> pluca.cache.remove_all()


### Flushing, garbage collection, shutdown

You can do garbage collection and flush all Global Cache API caches at
once:

    >>> pluca.cache.flush()
    >>> pluca.cache.gc()

Both `remove()` and `remove_all()` functions shut down removed caches
automatically. To prevent this, pass _False_ in `shutdown`:

    >>> pluca.cache.basic_config()
    >>>
    >>> pluca.cache.remove(shutdown=False)
    >>> pluca.cache.remove_all(shutdown=False)


## Composite caches

The `pluca.comp` backend chains multiple caches into a single cache.
Writes go to every configured child cache, reads return the first hit,
and `remove()` attempts deletion on every tier before raising
`KeyError`.

    >>> import pluca.comp
    >>> import pluca.memory
    >>> import pluca.file
    >>> comp_cache = pluca.comp.Cache()
    >>> comp_cache.add_cache(pluca.memory.Cache(max_entries=100))
    >>> comp_cache.add_cache(pluca.file.Cache(name='comp-example'))

You can also configure child caches from dict-like configuration
objects:

    >>> cfg_cache = pluca.comp.Cache([
    ...     {'factory': 'pluca.memory', 'max_entries': 10},
    ...     {'factory': 'pluca.null'},
    ... ])

As with the Global Cache API, composite cache configuration supports
`allowed_class_modules` when loading factories dynamically.


Caveats
-------

* Cache keys are internally mapped using the `repr()` of
  `(type(key), key)`, then hashed. As long as your key objects have stable
  representations, this will cause no problems. However, for types
  with unstable representation, for example those that have no
  inherent ordering (e.g., _frozenset_), this can be problematic
  because there’s no guarantee that `repr((type(key), key))` will
  return the same string value every time. This applies even to
  objects deep inside your key. The type is part of the mapping, so
  `1` and `'1'` are distinct keys. For example, this is a bad
  composite key:

        >>> key = ('foo', ('another', set((1, 2, 3))))  # set is unstable

* By default _pluca_ uses
  [pickle](https://docs.python.org/3/library/pickle.html) to serialize
  and unserialize data. A quote from the Python documentation:

  > It is possible to construct malicious pickle data which will
  > execute arbitrary code during unpickling. Never unpickle data that
  > could have come from an untrusted source, or that could have been
  > tampered with.

  So be careful where you store your cached data.

* The `sqlite3` backend only accepts simple SQL identifiers for dynamic
  names used in statements (for example PRAGMA names). Identifiers must
  match `[A-Za-z_][A-Za-z0-9_]*`; invalid names raise `ValueError`
  during cache initialization.

* The `file` backend defaults to `name='pluca'`. If `cache_dir` is not
  provided, it uses `appdirs.user_cache_dir()` when `appdirs` is
  installed, otherwise `~/.cache`. The cache `name` must be a single
  safe path segment: it cannot be absolute, cannot contain `/` or `\\`,
  and cannot be `.` or `..`.

  File locking can be controlled with the `locking` argument:

  - `locking='auto'` (default) selects the most efficient stdlib lock
    mechanism for the current OS.
  - `locking=None` disables file locking.
  - `locking='mkdir'` uses lock directories and is suitable when cache
    files are on NFS.
  - `locking='flock'` (POSIX) and `locking='msvcrt'` (Windows) force a
    specific stdlib lock mechanism.

  For `locking='mkdir'`, these options control lock waiting and stale
  lock cleanup:

  - `mkdir_stale_age` (default `300.0` seconds)
  - `mkdir_wait_timeout` (default `30.0` seconds)
  - `mkdir_poll_interval` (default `0.05` seconds)

  Lock ownership metadata is written to `<entry>.lock/owner` as three
  newline-separated values: PID, hostname, and creation timestamp.

  Locks are applied to each entry file. On POSIX (`flock`), reads use a
  shared lock and writes/removals use an exclusive lock. On Windows
  (`msvcrt`), reads and writes both use exclusive locking.

* `pluca.utils.create_cachedir_tag()` can create a `CACHEDIR.TAG` file
  for cache directories managed by your application:

        >>> import tempfile
        >>> import pluca.utils
        >>> tmp = tempfile.TemporaryDirectory()
        >>> pluca.utils.create_cachedir_tag(tmp.name)


Included backends
-----------------

These are the cache backends that come with the _pluca_ package:

- *file* - store cache entries on the file system.

- *sqlite3* - store cache entries in a SQLite3 database.

- *memory* - a memory-only cache that exists for the duration of the
  cache instance.

- *comp* - compose multiple caches into a tiered cache.

- *dbm* - store cache entries using DBM “databases”.

- *null* - the null cache - `get()` always raises _KeyError_.

The core package supports SQLite for SQL storage.

To obtain help about those cache backends, run
`help(pluca.MODULE.Cache)`, where _MODULE_ is one of the module names
above.


Benchmarking
------------

The _pluca.benchmark_ module can be used to benchmark the backends:

```console
$ python -m pluca.benchmark
```

Pass `-h` to see the benchmark options.

For deterministic stdlib-only behavior across platforms, DBM benchmarking
uses `dbm.dumb`.


Issues? Bugs? Suggestions?
--------------------------
Visit: https://github.com/flaviovs/pluca
