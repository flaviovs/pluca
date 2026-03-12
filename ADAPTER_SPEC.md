# pluca Adapter Specification

This document defines the contract you must follow to create a new cache
adapter for `pluca`.

If you follow this specification, your adapter should work with `pluca.Cache`
and with pluca configuration APIs.

## Example names

This document uses `pluca_xyz` as an example adapter module name.

## Compatibility targets

Your adapter should:

- support Python 3.11+
- depend on `pluca`
- preserve `pluca.Cache` public behavior

## What you implement

Implement an adapter class that satisfies `pluca.adapter.CacheAdapter`.

Example export:

```python
# pluca_xyz/__init__.py
from .adapter import XyzAdapter

Adapter = XyzAdapter
```

## Required adapter methods

Your adapter must provide these public methods:

- `put_mapped(mkey, value, max_age=None) -> None`
- `get_mapped(mkey) -> Any`
- `remove_mapped(mkey) -> None`
- `flush() -> None`
- `gc() -> None`
- `shutdown() -> None`

Misses and expired entries must raise:

- `KeyError(mkey)`

For invalid adapter configuration, raise:

- `ValueError`

## Utility methods and native optimizations

`pluca.Cache` offers utility APIs such as `has`, `put_many`, `get_many`, and
`remove_many`.

If your backend infrastructure supports these operations natively, you should
implement the corresponding adapter methods for better performance:

- `has_mapped(mkey) -> bool`
- `put_many_mapped(data, max_age=None) -> None`
- `get_many_mapped(keys, default=...) -> list[tuple[Any, Any]]`
- `remove_many_mapped(keys) -> None`

If native support is unavailable, keep these methods present and raise
`NotImplementedError`. `pluca.Cache` will automatically fallback to
single-item logic.

Example: if your backend has a native multi-set command, implement
`put_many_mapped` using that command instead of per-item writes.

## Expiration behavior

Public behavior must be consistent:

- `max_age=None`: no explicit expiration
- `max_age < 0`: invalid (`ValueError` from public API)
- `max_age == 0`: valid, behaves as immediately expired
- expired entries behave like missing entries

How expiration is enforced depends on your backend:

- If your backend supports native expiration (for example, memcache TTL), use
  native expiration.
- If it does not, enforce expiration in Python in adapter logic.

Both approaches are valid as long as API behavior stays consistent.

## Constructor guidance

Keep constructor arguments configuration-friendly:

- use simple scalar types when possible (`str`, `int`, `float`, `bool`,
  `None`)
- validate arguments early
- raise `ValueError` for invalid values

Important: requiring live runtime objects in constructor arguments (for
example, open connections, pre-built clients, sockets) prevents your adapter
from being usable from dict/file-based pluca configuration.

## Minimal skeleton

```python
import pickle
import time
from collections.abc import Iterable, Mapping
from typing import Any


class XyzAdapter:
    def __init__(self, endpoint: str, namespace: str | None = None) -> None:
        if not endpoint:
            raise ValueError('endpoint must be non-empty')
        if namespace == '':
            raise ValueError('namespace must not be empty')
        self.endpoint = endpoint
        self.namespace = namespace
        self._storage: dict[str, tuple[bytes, float | None]] = {}

    def _k(self, mkey: Any) -> str:
        base = str(mkey)
        if self.namespace is None:
            return base
        return f'{self.namespace}:{base}'

    def put_mapped(self, mkey: Any, value: Any,
                   max_age: float | None = None) -> None:
        expires = None if max_age is None else time.time() + max_age
        self._storage[self._k(mkey)] = (pickle.dumps(value), expires)

    def get_mapped(self, mkey: Any) -> Any:
        key = self._k(mkey)
        try:
            payload, expires = self._storage[key]
        except KeyError as ex:
            raise KeyError(mkey) from ex

        if expires is not None and expires <= time.time():
            del self._storage[key]
            raise KeyError(mkey)

        return pickle.loads(payload)

    def remove_mapped(self, mkey: Any) -> None:
        key = self._k(mkey)
        try:
            del self._storage[key]
        except KeyError as ex:
            raise KeyError(mkey) from ex

    def flush(self) -> None:
        self._storage.clear()

    def has_mapped(self, mkey: Any) -> bool:
        raise NotImplementedError

    def put_many_mapped(self,
                        data: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
                        max_age: float | None = None) -> None:
        raise NotImplementedError

    def get_many_mapped(self, keys: Iterable[Any],
                        default: Any = ...) -> list[tuple[Any, Any]]:
        raise NotImplementedError

    def remove_many_mapped(self, keys: Iterable[Any]) -> None:
        raise NotImplementedError

    def gc(self) -> None:
        now = time.time()
        expired = [
            key for key, (_, exp) in self._storage.items()
            if exp is not None and exp <= now
        ]
        for key in expired:
            del self._storage[key]

    def shutdown(self) -> None:
        return None


Adapter = XyzAdapter
```

## HOWTO: basic adapter test with AdapterTester

Use `pluca.test.AdapterTester` to validate core behavior.

```python
import unittest

import pluca_xyz
from pluca.test import AdapterTester


class TestXyz(AdapterTester, unittest.TestCase):
    def get_adapter(self) -> pluca_xyz.Adapter:
        return pluca_xyz.Adapter(endpoint='127.0.0.1:11211')
```

This checks behavior through `pluca.Cache` wrapping and validates standard
cache semantics.

Then add backend-specific tests for features such as:

- connection/auth failures
- native TTL handling
- native bulk operation behavior
- resource lifecycle in `shutdown()`

## Final rule

If an optimization conflicts with standard `pluca.Cache` behavior, preserve
standard behavior.
