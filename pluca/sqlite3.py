import pickle
import re
import sqlite3
import time
from collections.abc import Iterable, Mapping
from typing import Any

_VALID_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _validate_identifier(name: str, kind: str) -> str:
    if not _VALID_IDENTIFIER.fullmatch(name):
        raise ValueError(f'Invalid SQLite {kind} identifier: {name!r}')
    return name


class SQLite3Adapter:
    """SQLite3 cache adapter for pluca."""

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
            for name, value in pragma.items():
                _validate_identifier(name, 'PRAGMA')
                self._conn.execute(f'PRAGMA {name} = {value!r}')

        self._conn.execute(f'CREATE TABLE IF NOT EXISTS {self._table} ('
                           f'{self._k_col} VARCHAR PRIMARY KEY, '
                           f'{self._v_col} BLOB NOT NULL, '
                           f'{self._exp_col} FLOAT) '
                           'WITHOUT ROWID')

        self.filename = filename

    def _commit(self) -> None:
        if self._conn.in_transaction:
            self._conn.commit()

    def put_mapped(self, mkey: Any, value: Any,
                   max_age: float | None = None) -> None:
        svalue = pickle.dumps(value)
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
        self._commit()

    def put_many_mapped(self,
                        data: Mapping[Any, Any] | Iterable[tuple[Any, Any]],
                        max_age: float | None = None) -> None:
        if isinstance(data, Mapping):
            data = data.items()

        expires = None if max_age is None else time.time() + max_age
        values = []
        for mkey, value in data:
            svalue = pickle.dumps(value)
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

    def get_mapped(self, mkey: Any) -> Any:
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
        return pickle.loads(row[0])

    def get_many_mapped(self, keys: Iterable[Any],
                        default: Any = ...) -> list[tuple[Any, Any]]:
        all_mkeys = list(dict.fromkeys(keys))
        if not all_mkeys:
            return []

        in_list = ', '.join([self._ph] * len(all_mkeys))
        args: list[Any] = list(all_mkeys)
        args.append(time.time())

        values_by_key: dict[Any, Any] = {}

        cur = self._conn.cursor()
        cur.execute(f'SELECT {self._k_col}, {self._v_col} '
                    f'FROM {self._table} '
                    f'WHERE {self._k_col} IN ({in_list}) '
                    f'AND ({self._exp_col} IS NULL '
                    f'OR {self._exp_col} > {self._ph})',
                    tuple(args))

        for row in cur.fetchall():
            values_by_key[row[0]] = pickle.loads(row[1])

        cur.close()

        if default is not Ellipsis:
            for key in all_mkeys:
                if key not in values_by_key:
                    values_by_key[key] = default

        result = []
        for key in all_mkeys:
            if key in values_by_key:
                result.append((key, values_by_key[key]))
        return result

    def remove_mapped(self, mkey: Any) -> None:
        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table} '
                    f'WHERE {self._k_col} = {self._ph}',
                    (mkey,))
        rowcount = cur.rowcount
        cur.close()
        self._commit()
        if rowcount == 0:
            raise KeyError(mkey)

    def remove_many_mapped(self, keys: Iterable[Any]) -> None:
        items = tuple(keys)
        if not items:
            return

        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table} '
                    f'WHERE {self._k_col} '
                    f'IN ({", ".join([self._ph] * len(items))})',
                    items)
        cur.close()
        self._commit()

    def flush(self) -> None:
        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table}')
        cur.close()
        self._commit()

    def has_mapped(self, mkey: Any) -> bool:
        cur = self._conn.cursor()
        cur.execute('SELECT EXISTS('
                    f'SELECT * FROM {self._table} '
                    f'WHERE {self._k_col} = {self._ph} '
                    f'AND ({self._exp_col} IS NULL '
                    f'OR {self._exp_col} > {self._ph}))',
                    (mkey, time.time()))
        has = bool(cur.fetchone()[0])
        cur.close()
        return has

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


Adapter = SQLite3Adapter
