Plugable cache architecture for Python
=======================================

*pluca* is a plugable cache architecture for Python 3
applications. The package provides an unified interface to several
cache adapters, which allows an application to switch cache back-ends
on an as-needed basis with minimal or no code changes.

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

```python
from pluca.file import create  # Import file back-end factory function.

# Create the cache object.
cache = create()

# Put something on the cache.
cache.put('pi', 3.1415)

# Retrieve the value from the cache.
pi = cache.get('pi')
print(type(pi), pi)
# Output:
# <class 'float'> 3.1415

# Handle non-existent/expired cache entries.
try:
	cache.get('notthere')
except KeyError:
	print('Not found on cache')
	
# Handle non-existent/expired entries with a default.
value = cache.get('notthere', 12345)
print(value)  # Output: 12345

# Set expiration.
cache.put('see-you', 'in three secs', 3)  # Expire the entry in 3 seconds.
import time; time.sleep(4)
cache.get('see-you')
# KeyError: 'see-you'

# Composite keys.
key = (__name__, True, 'this', 'key', 'has', 'more', 'than', 1, 'value')
cache.put(key, 'data')
print(cache.get(key))  # Outputs: 'data'

# Abstract the cache back-end.
from math import factorial
def cached_factorial(cache, n):
	try:
		res = cache.get(('factorial', n))
	except KeyError:
		print(f'Calculating {n}!')
		res = factorial(n)
		cache.put(('factorial', n), res)
	return res

print(cached_factorial(cache, 10))  # NB: Using file cache.
# Output:
# Calculating 10!

print(cached_factorial(cache, 10))  # NB: Using file cache.
# Output: 3628800

# Now let's switch to the "null" back-end.
from pluca.null import create as create_null
null_cache = create_null()

print(cached_factorial(null_cache, 10))  # NB: Using file cache.
# Output:
# Calculating 10!

print(cached_factorial(null_cache, 10))  # NB: Using file cache.
# Output:
# Calculating 10!
```

Included back-ends
------------------

- *file* - store cache entries on file system entries
- *memory* - a memory-only cache that exists for the duration of the cache instance
- *null* - the null cache - `get()` always raises `KeyError`


Issues? Bugs? Suggestions?
--------------------------
Visit: https://github.com/flaviovs/pluca
