# Changelog

All notable changes to this project are documented in this file.

This project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Entries marked as **BC BREAK** indicate backward-incompatible changes.

## [Unreleased]

### Added

- A new `CompositeCache` backend for composing multiple cache strategies.
- New cache utility helpers, including `create_cachedir_tag()` and shared
  cache-creation logic.
- New global cache helpers: `flush()`, `gc()`, and a `shutdown` option for
  `remove()`/`remove_all()`.
- `None` can now be used as an alias for the root/global cache.
- DBM backend support for `pathlib.Path` values.
- A `task spellcheck` command powered by `codespell`.
- Optional class-loading allowlists for dynamic cache configuration APIs
  (`dict_config()`, `file_config()`, and composite cache config loading).

### Fixed

- `FileCache` cache names are hardened against path traversal inputs.
- `FileCache.flush()` and `FileCache.gc()` are now safe no-ops on fresh
  caches (or after cache-directory removal) instead of raising
  `FileNotFoundError`.
- Global `pluca.cache.gc()` now behaves correctly even when a backend does not
  implement GC.
- Root cache removal is now idempotent (safe to call multiple times).
- DBM now respects `max_age` correctly.
- `max_age=0` now expires entries immediately across memory, DBM, and SQL
  backends.
- Global `file_config()` now coerces INI booleans and numeric values before
  passing backend kwargs, avoiding delayed type errors at runtime.
- SQLite3 `put_many()` is now atomic and commits once per call, avoiding
  partial writes when a batch entry fails.
- SQLite3 batch reads/removals now explicitly support empty key iterables,
  and regression tests cover empty list/tuple/generator inputs to prevent
  `IN ()` SQL regressions.
- `CompositeCache.remove()` now attempts all tiers before failing, so a
  miss in an upper tier no longer leaves stale values in lower tiers.
- SQLite3 now validates SQL identifiers used for dynamic names (including
  PRAGMA directives) and rejects invalid inputs with `ValueError`.
- Developer-quality fixes: restored missing mypy overrides, fixed test file
  encoding warnings, and cleaned spelling/docs issues.
- DBM tests are now stdlib-portable and no longer skip when optional DBM
  variants are unavailable.
- `get_child(None, child)` and `get_child('', child)` now resolve the same
  node as `get_cache(child)` instead of building a leading-dot path.
- `tests.test_utils.TestUtils._assert_cache_dir_tag` now checks
  `Path.is_file()` correctly, so missing `CACHEDIR.TAG` files fail with a
  clear assertion.

### Changed

- **BC BREAK:** The project now requires Python 3.11+.
- SQLite3 now creates new cache tables with `WITHOUT ROWID`.
- **BC BREAK:** Internal cache ABC method names were standardized (`key` ->
  `mkey`, `flush` -> `_flush`), which may require updates in custom backend
  subclasses.
- **BC BREAK:** Core SQL support no longer includes PostgreSQL and MySQL
  specific behavior. PostgreSQL/MySQL support will move to separate packages.
- **BC BREAK:** Removed the generic `pluca.sql` backend from core.
  Core SQL cache support is now SQLite-only via `pluca.sqlite3`.
- Packaging/build system moved to Flit.

### Removed

- PostgreSQL/MySQL integration tests from the core repository.
- Docker-based test infrastructure used for PostgreSQL/MySQL integration tests.
- The `pluca.sql` module from the core package.

## [0.6.0] - 2023-02-17

### Added

- `remove_many()` and `shutdown()` APIs for better lifecycle and bulk-removal
  control.
- A SQLite3 backend.
- DBM backend support for direct DBM file-name inputs.

### Fixed

- SQL backend `__repr__` output was corrected.
- File backend writes now use temporary files to reduce race-condition risks in
  concurrent scenarios.

## [0.5.0] - 2023-02-17

### Added

- A benchmark module.
- A `prune` option in the memory backend for bounded in-memory cache behavior.

### Fixed

- Memory backend serialization now behaves correctly.
- Memory backend garbage collection now correctly removes expired entries.
- Expanded linting quality checks (`pylint` extensions), disallowed `print()`,
  and cleaned up backend representation/dataclass consistency.

## [0.4.0] - 2023-02-15

### Added

- SQL and DBM backends.
- `file_config()` in the global cache API.
- SQL placeholder customization for cross-driver compatibility.
- SQL support for MySQL `INSERT ... ON DUPLICATE` upserts.
- PostgreSQL and MariaDB/MySQL test suites.
- Docker Compose support for DB integration tests and multi-Python test runs.

### Fixed

- File backend persistence of pickled data is more robust.
- Generic cache contract tests now explicitly exercise `gc()` behavior.
- SQL backend now properly implements garbage collection.
- DBM tests no longer leave temporary files behind.
- `get_many()` now handles `None` defaults correctly.
- `put()` now validates `max_age` inputs.
- Added a pickle-security note and other README improvements.

## [0.3.0] - 2023-02-14

### Added

- Utility developer tasks and a QA script.
- Generic tests for key-type behavior.

### Fixed

- Decorator use with parameters no longer raises unexpected exceptions.
- Null adapter signatures and methods were corrected/simplified.
- `Cache` base class abstractness issue was fixed.
- `get_many()`/`put_many()` now work better with dict inputs.
- Typing coverage and mypy configuration were improved.
- Expanded README caveats/examples and improved class docstrings.

### Changed

- **BC BREAK:** Global cache API was refactored for a simpler developer-facing
  interface.
- **BC BREAK:** Adapter classes were removed, which may require migration for
  integrations relying on adapter-specific APIs.
- **BC BREAK:** Key mapping internals changed (`_get_cahe_key` -> `_map_key`)
  and key derivation now uses `repr((type, key))`, which can change cache-key
  values across upgrades.
- File backend cache name/directory mapping was refactored for clearer behavior.

## [0.2.0] - 2021-12-27

### Changed

- **BC BREAK:** Renamed the cache-interface `cache_name` field to avoid naming
  conflicts in integrations.

## [0.1.2] - 2021-12-21

### Added

- Dynamic cache interface support.
- Decorator-based caching support.

## [0.1.1] - 2021-12-20

### Changed

- Packaging metadata now includes the README in `setup.cfg`.
- Version handling switched to dynamic versioning for cleaner release
  management.

## [0.1.0] - 2021-12-20

### Added

- Initial public project packaging and scaffolding.
- README and package classifiers.
- Initial unit test suite, including behavior for removing missing keys.
- Memory and null cache adapters.

### Changed

- Early cache interface and adapter naming were refactored during initial
  release preparation.
- Default cache-key hashing switched to SHA1.
