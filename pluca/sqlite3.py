import sqlite3
import time
import re
from collections.abc import Iterable, Mapping
from typing import Any

import pluca

_VALID_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _validate_identifier(name: str, kind: str) -> str:
    if not _VALID_IDENTIFIER.fullmatch(name):
        raise ValueError(f'Invalid SQLite {kind} identifier: {name!r}')
    return name


class SQLite3Cache(pluca.Cache):
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
            on the connection. Directive names must be valid SQLite
            identifiers (`[A-Za-z_][A-Za-z0-9_]*`).
        **kwargs: All other arguments are passed unchanged to
            `sqlite3.connect()`.

    """

    def __init__(self,
                 filename: str,
                 pragma: Mapping[str, str | float | bool] | None = None,
                 **kwargs: Any) -> None:
        self._conn = sqlite3.connect(filename, **kwargs)
        self._table = 'cache'
        self._k_col = 'k'
        self._v_col = 'v'
        self._exp_col = 'expires'
        self._ph = '?'

        _validate_identifier(self._table, 'table')
        _validate_identifier(self._k_col, 'column')
        _validate_identifier(self._v_col, 'column')
        _validate_identifier(self._exp_col, 'column')

        if pragma:
            for (name, value) in pragma.items():
                _validate_identifier(name, 'PRAGMA')
                self._conn.execute(f'PRAGMA {name} = {value!r}')

        self.__check_table()

        self.filename = filename

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}('
                f'filename={self.filename!r}, '
                f'table={self._table!r}, '
                f'k_column={self._k_col!r}, '
                f'v_column={self._v_col!r}, '
                f'expires_column={self._exp_col!r})')

    def __check_table(self) -> None:
        self._conn.execute(f'CREATE TABLE IF NOT EXISTS {self._table} ('
                           f'{self._k_col} VARCHAR PRIMARY KEY, '
                           f'{self._v_col} BLOB NOT NULL, '
                           f'{self._exp_col} FLOAT) '
                           'WITHOUT ROWID')

    def _commit(self) -> None:
        if self._conn.in_transaction:
            self._conn.commit()

    def _put(self, mkey: Any, value: Any,
             max_age: float | None = None) -> None:
        svalue = self._dumps(value)
        expires = None if max_age is None else time.time() + max_age

        cur = self._conn.cursor()
        cur.execute(f'INSERT INTO {self._table} '
                    f'({self._k_col}, {self._v_col}, {self._exp_col}) '
                    f'VALUES ({self._ph}, {self._ph}, {self._ph}) '
                    f'ON CONFLICT({self._k_col}) DO UPDATE SET '
                    f'{self._v_col} = {self._ph}, '
                    f'{self._exp_col} = {self._ph}',
                    (mkey, svalue, expires, svalue, expires))
        cur.close()

    def _get(self, mkey: Any) -> Any:
        cur = self._conn.cursor()
        cur.execute(f'SELECT {self._v_col}, {self._exp_col} '
                    f'FROM {self._table} '
                    f'WHERE {self._k_col} = {self._ph} '
                    f'AND ({self._exp_col} IS NULL '
                    f'OR {self._exp_col} > {self._ph})',
                    (mkey, time.time()))
        row = cur.fetchone()
        cur.close()
        if not row:
            raise KeyError(mkey)
        return self._loads(row[0])

    def _remove(self, mkey: Any) -> None:
        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table} '
                    f'WHERE {self._k_col} = {self._ph}',
                    (mkey,))
        rowcount = cur.rowcount
        cur.close()
        if rowcount == 0:
            raise KeyError(mkey)

    def _flush(self) -> None:
        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table}')
        cur.close()

    def _has(self, key: Any) -> bool:
        cur = self._conn.cursor()
        cur.execute('SELECT EXISTS('
                    f'SELECT * FROM {self._table} '
                    f'WHERE {self._k_col} = {self._ph} '
                    f'AND ({self._exp_col} IS NULL '
                    f'OR {self._exp_col} > {self._ph}))',
                    (key, time.time()))
        has = bool(cur.fetchone()[0])
        cur.close()
        return has

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
        """Store multiple values atomically and commit once.

        Args:
            data: Mapping or iterable of ``(key, value)`` pairs.
            max_age: Maximum age in seconds applied to all entries.

        Raises:
            ValueError: If ``max_age`` is negative.

        """
        if max_age and max_age < 0:
            raise ValueError('Cache max_age must be greater or equal to zero, '
                             f'got {max_age}')

        if isinstance(data, Mapping):
            data = data.items()

        expires = None if max_age is None else time.time() + max_age
        values = []
        for (key, value) in data:
            mkey = self._map_key(key)
            svalue = self._dumps(value)
            values.append((mkey, svalue, expires, svalue, expires))

        if not values:
            return

        started_transaction = False
        if not self._conn.in_transaction:
            self._conn.execute('BEGIN')
            started_transaction = True

        cur = self._conn.cursor()
        try:
            cur.executemany(f'INSERT INTO {self._table} '
                            f'({self._k_col}, {self._v_col}, {self._exp_col}) '
                            f'VALUES ({self._ph}, {self._ph}, {self._ph}) '
                            f'ON CONFLICT({self._k_col}) DO UPDATE SET '
                            f'{self._v_col} = {self._ph}, '
                            f'{self._exp_col} = {self._ph}',
                            values)
        except sqlite3.Error:
            if started_transaction and self._conn.in_transaction:
                self._conn.rollback()
            raise
        finally:
            cur.close()

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
        items = tuple(self._map_key(k) for k in keys)
        if not items:
            return

        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table} '
                    f'WHERE {self._k_col} '
                    f'IN ({", ".join([self._ph] * len(items))})',
                    items)
        cur.close()
        self._commit()

    def get_many(self, keys: Iterable[Any],
                 default: Any = ...) -> list[tuple[Any, Any]]:
        """Fetch multiple keys in one query.

        Args:
            keys: Iterable of cache keys.
            default: Value to use for missing keys. If omitted, missing keys
                are excluded.

        Returns:
            A list of ``(key, value)`` tuples.

        """
        all_keys = {self._map_key(k): k for k in keys}
        if not all_keys:
            return []

        in_list = ', '.join([self._ph] * len(all_keys))
        args: list[Any] = list(all_keys.keys())
        args.append(time.time())

        res = []

        cur = self._conn.cursor()
        cur.execute(f'SELECT {self._k_col}, {self._v_col} '
                    f'FROM {self._table} '
                    f'WHERE {self._k_col} IN ({in_list}) '
                    f'AND ({self._exp_col} IS NULL '
                    f'OR {self._exp_col} > {self._ph})',
                    tuple(args))

        for row in cur.fetchall():
            key = all_keys.pop(row[0])
            res.append((key, self._loads(row[1])))
        cur.close()

        if default is not Ellipsis:
            res.extend((k, default) for k in all_keys.values())

        return res

    def flush(self) -> None:
        """Remove all entries and commit when needed."""
        super().flush()
        self._commit()

    def gc(self) -> None:
        """Delete expired rows, commit, and optimize the database."""
        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table} '
                    f'WHERE {self._exp_col} <= {self._ph}',
                    (time.time(),))
        cur.close()
        self._commit()
        self._conn.execute('PRAGMA optimize')

    def shutdown(self) -> None:
        """Close the SQLite connection."""
        self._conn.close()


Cache = SQLite3Cache
