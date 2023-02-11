Plugable cache architecture for Python
=======================================

*pluca* is a plugable cache architecture for Python 3
applications. The package provides an unified interface to several
cache adapters, which allows an application to switch cache back-ends
on an as-needed basis with minimal changes.

Features
--------
- Unified cache interface - your application can just instantiate a
  `Cache` object and pass it around -- client code just access the
  cache without having to know any of the details about caching
  back-ends, expiration logic, etc.
- Easy interface - writing a *pluca* adapter for a new caching back-end
  is very straightforward
- It is fast - the library is developed with performance in mind
- It works out-of-box - a *file* adapter is provided that can be used
  for file system caching
- No batteries needed - *pluca* has no external dependencies

How to use
----------

First import the cache adapter factory:

    >>> from pluca.file import create  # Let's user the file system adapter.

Now create the cache object:

    >>> cache = create()

Put something on the cache:

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

You can provide a default value for non-existent/expired entries:

    >>> cache.get('notthere', 12345)
    12345

By default cache entries are set to “never” expire — cache adapters
can expire entries though, for example to use less resource. Here’s an
example of how to store a cache entry with an explicit expiration
time:

    >>> cache.put('see-you', 'in two secs', 2)  # Expire in 2 seconds.
    >>> import time; time.sleep(3)  # Wait for it to expire.
    >>> cache.get('see-you')
    Traceback (most recent call last):
        ...
    KeyError: 'see-you'

Cache keys can be any hashable:

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
store the data anywhere — see `help(pluca.null.CacheAdapter)` for more
info):

    >>> import pluca.null
    >>> null_cache = pluca.null.create()
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

    >>> @cache(max_age=2)  # Expire after two seconds.
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

    >>> import time; time.sleep(2)
    >>> quick_calculation(1, 2)
    Calculating 1 + 2
    3


## Miscelaneous

Use `get_put()` to conveniently get a value from the cache, or call a
function to generate it, if it is not cached already:

    >>> try:
    ...     cache.remove('foo')
    ... except KeyError:
    ...     pass
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

You can also put and get many entries at once:

    >>> cache.put_many({'foo': 'bar', 'zee': 'too'})
    >>> cache.get('zee')
    'too'
    >>> cache.put('pi', 3.1415)
    >>> cache.get_many(['zee', 'pi'])
    {'zee': 'too', 'pi': 3.1415}

Notice that `get_many()` does **not* raise `KeyError` when a key does
not exist. Instead, the key will not be present on the returned dict:

    >>> cache.get_many(['pi', 'not-there'])
    {'pi': 3.1415}


The cache adapter object can be accessed in the `adapter` attribute:

     >>> type(cache.adapter)
     <class 'pluca.file.CacheAdapter'>
     >>> cache.adapter # doctest: +ELLIPSIS
     CacheAdapter(path=..., name=...)

## Garbage collection.

Garbage collection tells the cache to remove expired entries to save
resources. This is done by the `gc()` method:

    >>> cache.gc()

Notice that **pluca never calls `gc()` automatically** — it is up to
your application to call it eventually to do garbage collection.


Included back-ends
------------------

These are the cache back-ends that come with the _pluca_ package:

- *file* - store cache entries on the file system
- *memory* - a memory-only cache that exists for the duration of the
  cache instance
- *null* - the null cache - `get()` always raises `KeyError`


Issues? Bugs? Suggestions?
--------------------------
Visit: https://github.com/flaviovs/pluca
