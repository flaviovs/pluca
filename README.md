Plugable cache architecture for Python
=======================================

*pluca* is a plugable cache architecture for Python 3
applications. The package provides an unified interface to several
cache implementations, which allows an application to switch cache
back-ends on an as-needed basis with minimal changes.

Features
--------
- Unified cache interface - your application can just instantiate a
  `Cache` object and pass it around — client code just access the
  cache without having to know any of the details about caching
  back-ends, expiration logic, etc.
- Easy interface - writing a *pluca* cache for a new caching back-end
  is very straightforward
- It is fast - the library is developed with performance in mind
- It works out-of-box - a file system cache is provided that can be
  used out-of-box
- No batteries needed - *pluca* has no external dependencies

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

To test if a entry exists, use `has()`:

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

Flushing the cache remove all entries:

    >>> cache.put('bye', 'tchau')
    >>> cache.flush()
    >>> cache.get('bye')
    Traceback (most recent call last):
        ...
    KeyError: 'bye'

## Abstracting cache back-ends

Here’s how to abstract cache back-ends. First, let’s define a function
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

Now let's switch to the “null” back-end (the “null” back-end does not
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

You can add get many entries to the cache at once by calling
`put_many()`:

    >>> cache.put_many({'foo': 'bar', 'zee': 'too'})
    >>> cache.get('zee')
    'too'

You can also pass an iterable of _(key, value)_ tuples. This is is
useful for caching with non-hashable keys:

    >>> cache.put_many([(['a', 'b', 'c'], 123), ('pi', 3.1415)])
    >>> cache.get(['a', 'b', 'c'])
    123

Use `get_many()` to get many results at once. This method returns a
list of _(key, value)_ tuples:

    >>> cache.get_many(['zee', 'pi'])
    [('zee', 'too'), ('pi', 3.1415)]

Notice that `get_many()` does **not** raise _KeyError_ when a key is
not found or has expired. Instead, the key will not be present in the
returned dict:

    >>> cache.get_many(['pi', 'not-there'])
    [('pi', 3.1415)]

However, you can pass a default value to `get_many()`. This value will
be returned for any non-existing keys:

    >>> cache.get_many(['pi', 'not-there', 'also-not-there'], default='yes')
    [('pi', 3.1415), ('not-there', 'yes'), ('also-not-there', 'yes')]


## Garbage collection.

Garbage collection tells the cache to remove expired entries to save
resources. This is done by the `gc()` method:

    >>> cache.gc()

Notice that **pluca never calls `gc()` automatically** — it is up to
your application to call it eventually to do garbage collection.


Global Cache API
----------------

_pluca_ comes with a separate cache API that allows libraries and
application to benefit from caching in a very flexible way. In one
hand, it allows libraries that would benefit from caching to use
_pluca_ even if the calling applications doesn’t support it. On the
other hand, an application that does support _pluca_ can customize
caches for specific libraries without any extra API.

In the sections below you will see how the Global Cache API works both
from a library and a application perspective, but before it is
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

Then a look up of “pkg.mod” would return the null cache. If you look
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
a single application using a single cache, you can just call
`pluca.cache.basic_config()`:

    >>> pluca.cache.basic_config()

This sets up a file cache as the root cache. If desired, you can use
another cache back-end:

    >>> # Configure a memory cache as the cache root.
    >>> pluca.cache.basic_config('memory')

You can also customize the cache object:

    >>> pluca.cache.basic_config('file', cache_dir='/tmp')

**Note**: when you call `basic_config()` all existing caches are
removed before the new one is set up.

To configure additional caches, use `pluca.cache.add()`:

    >>> pluca.cache.add('mod', 'memory', max_entries=100)
    >>> pluca.cache.add('pkg.foo', 'null')

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


A call from another random module would return the root (file) cache:

    >>> # In another.py
    >>> cache = pluca.cache.get_cache(__name__)
    >>> cache  # doctest: +ELLIPSIS
    FileCache(name=..., cache_dir=...)

**NOTE**: a root cache is always required. If don’t set up the root
cache, then `pluca.cache.basic_config()` will be called to set up one
for you.

The function `add()` has the following signature:

```python
add(node: str, cls: str, reuse: bool = True, **kwargs: Any)
```

Here, `node` is the cache node name. `cls` indicates the cache class
you want to instantiate for that node.

The `cls` parameter must be a fully-qualified class name (for example,
`mycustomcache.Cache`). If `cls` is a string with no “.” (dot) in it,
i is assumed to be a cache class from the the standard _pluca_ package
— for example, `memory` is the same as `pluca.memory.Cache`.

By default, caches will reuse previously created instances with the
same `cls` name and arguments. For example, the two `get_cache()`
calls below return the same cache object:

    >>> pluca.cache.add('c1', 'file')
    >>> pluca.cache.add('c2', 'file')
    >>> pluca.cache.get_cache('c1') is pluca.cache.get_cache('c2')
    True

To prevent this from happening, pass _False_ on the `reuse` parameter:

    >>> pluca.cache.add('c3', 'file', reuse=False)
    >>> pluca.cache.get_cache('c2') is pluca.cache.get_cache('c3')
    False

The remaining arguments to the `add()` function are passed unchanged
to the cache class constructor.

    >>> pluca.cache.add('c4', 'file', name='c4', cache_dir='/tmp')
    >>> pluca.cache.get_cache('c4')
    FileCache(name='c4', cache_dir=PosixPath('/tmp'))

You can also configure the API using a dict-like object using
`pluca.cache.dict_config()`:

    >>> pluca.cache.dict_config({
    ...     'class': 'memory',  # The root cache.
    ...     'max_entries': 10,
    ...
    ...     'caches': {  # Configure extra caches.
    ...         'mod': {
    ...             'class': 'null',
    ...         },
    ...         'pkg.mod': {
    ...             'class': 'file',
    ...             'name': 'pkg_mod',
    ...             'cache_dir': '/tmp',
    ...         },
    ...     },
    ... })
    >>> pluca.cache.get_cache('mod')
    NullCache()

A facility to set up the API using a configuration file is also
provided. Heres an example:

    >>> from tempfile import NamedTemporaryFile
    >>>
    >>> temp = NamedTemporaryFile(mode='w+', suffix='.ini')
    >>> n = temp.write('''
    ...
    ...     [__root__]
    ...     class = memory
    ...     max_entries = 10
    ...
    ...     [mod]
    ...     class = null
    ...
    ...     [pkg.mod]
    ...     class = file
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


### Removing caches

To remove cache entries, call `pluca.cache.remove()`:

    >>> pluca.cache.remove('mod')

Notice that removing a cache does not remove its children:

    >>> pluca.cache.add('a.b', 'file')
    >>> pluca.cache.add('a.b.c', 'file')
    >>> pluca.cache.remove('a.b')
    >>> pluca.cache.get_cache('a.b.c')  # doctest: +ELLIPSIS
    FileCache(name=...)

To remove all cache entries and effectively reset the Global Cache
API, call `pluca.cache.remove_all()`:

    >>> pluca.cache.remove_all()


### Flushing, garbage collection

You can do garbage colletion and flush all Global Cache API caches at
once:

    >> pluca.cache.flush()
    >> pluca.cache.gc()


Caveats
-------

* Cache keys are internally converted to strings using Python’s
  `repr()` function. As long as your keys objects have stable
  representations, this will cause no problems. However, for types
  with unstable representation, for example those that have no
  inherent ordering (e.g., _frozenset_), this can be problematic
  because there’s no guarantee that `repr(key)` will return the same
  string value every time. This applies even to objects deep inside
  your key. For example, this is a bad composite key:

        >>> key = ('foo', ('another', set((1, 2, 3))))  # set is unstable

* By default _pluca_ uses
  [pickle](https://docs.python.org/3/library/pickle.html) to serialize
  and unserialize data. A quoted from the Python documentation:

  > It is possible to construct malicious pickle data which will
  > execute arbitrary code during unpickling. Never unpickle data that
  > could have come from an untrusted source, or that could have been
  > tampered with.

  So be careful where you store your cached data.


Included back-ends
------------------

These are the cache back-ends that come with the _pluca_ package:

- *dbm* - store cache entries usim DBM “databases”.

- *file* - store cache entries on the file system.

- *memory* - a memory-only cache that exists for the duration of the
  cache instance.

- *null* - the null cache - `get()` always raises _KeyError_.

- *sql* - store cache entries in SQL databases.

- *sqlite3* - store cache entries in a SQLite3 database. Based on the
  _sql_ back-end, but with SQLite3 specific functionalities.

To obtain help about those cache back-ends, run
`help(pluca.MODULE.Cache)`, where _MODULE_ is one of the module names
above.


Benchmarking
------------

The _pluca.benchmark_ module can be used to benchmark the back-ends:

```console
$ python -m pluca.benchmark
```

Pass `-h` to see the benchmark options.


Issues? Bugs? Suggestions?
--------------------------
Visit: https://github.com/flaviovs/pluca
