import sqlite3
from collections.abc import Iterable, Mapping
from typing import Any

from .sql import SqlCache


class SQLite3Cache(SqlCache):
    """SQLite3 cache for pluca.

    This cache store entries in a SQLite3 database.

    Example:

            cache = pluca.sqlite3.cache('/tmp/cache.db',
                                        pragma={'journal_mode': 'WAL'},
                                        isolation_level=None)

    Args:

        filename: The SQL database file name (pass ":memory:" for a
            in-memory database).
        pragma: A {key: value} mapping of PRAGMA directives to be set
            on the connection.
        **kwargs: All other arguments are passed unchanged to
            `sqlite3.connect()`.

    """

    # pylint: disable-next=too-many-arguments
    def __init__(self,
                 filename: str,
                 pragma: Mapping[str, str | float | bool] | None = None,
                 **kwargs: Any) -> None:
        super().__init__(sqlite3.connect(filename, **kwargs))

        if pragma:
            for (name, value) in pragma.items():
                self._conn.execute(f'PRAGMA {name} = {value!r}')

        self.__check_table()

        self.filename = filename

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}('
                f'filename={self.filename!r}, '
                f'table={self._table!r}, '
                f'k_column={self._k_col!r}, '
                f'v_column={self._v_col!r}, '
                f'expires_column={self._exp_col!r}')

    def __check_table(self) -> None:
        self._conn.execute(f'CREATE TABLE IF NOT EXISTS {self._table} ('
                           f'{self._k_col} VARCHAR PRIMARY KEY, '
                           f'{self._v_col} BLOB NOT NULL, '
                           f'{self._exp_col} FLOAT)')

    def _commit(self) -> None:
        if self._conn.in_transaction:
            self._conn.execute('COMMIT')

    def put(self, key: Any, value: Any,
            max_age: float | None = None) -> None:
        """Store a value and commit when needed.

        Args:
            key: Entry key.
            value: Value to cache.
            max_age: Maximum age in seconds.

        """
        super().put(key, value, max_age)
        self._commit()

    def put_many(self,
                 data: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
                 max_age: float | None = None) -> None:
        """Store multiple values and commit when needed.

        Args:
            data: Mapping or iterable of ``(key, value)`` pairs.
            max_age: Maximum age in seconds applied to all entries.

        """
        super().put_many(data, max_age)
        self._commit()

    def remove(self, key: Any) -> None:
        """Remove an entry and commit when needed.

        Args:
            key: Entry key.

        """
        super().remove(key)
        self._commit()

    def remove_many(self, keys: Iterable[Any]) -> None:
        """Remove multiple entries and commit when needed.

        Args:
            keys: Iterable of entry keys.

        """
        super().remove_many(keys)
        self._commit()

    def _flush(self) -> None:
        super()._flush()
        self._commit()

    def gc(self) -> None:
        """Delete expired rows, commit, and optimize the database."""
        super().gc()
        self._commit()
        self._conn.execute('PRAGMA optimize')

    def shutdown(self) -> None:
        """Close the SQLite connection."""
        self._conn.close()


Cache = SQLite3Cache
