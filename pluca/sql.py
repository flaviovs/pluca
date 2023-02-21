import time
from typing import Optional, Any, Iterable, List, Tuple

import pluca


class SqlCache(pluca.Cache):
    """SQL cache for pluca.

    SQL cache store cache entries on a SQL database. The table used to
    store cache entries is expected to be on the database already. You
    can create the table with the following SQL command:

        CREATE TABLE cache (
            k VARCHAR(40) NOT NULL PRIMARY KEY,
            v BLOB NOT NULL,
            expires FLOAT
        )

    You can pass parameters to the constructor to override the table
    and/or column names, if necessary.

    Note:
        The SQL cache does not keep track of database transactions. If
        the connection is not in "auto-commit" mode, you must
        explicitly issue database commits after write calls
        (e.g. `put()`, `remove()`, etc.), otherwise your changes will
        be lost if the current transaction is rolled back.

    Args:
        connection: A PEP 249 DB-ABI connection.
        table: The cache table name.
        k_column: The column name to store keys.
        v_column: The column name to store values.
        expires_column: The column name to store expiration timestamps.

    """

    def __init__(self,  # pylint: disable=too-many-arguments
                 connection: Any,
                 table: str = 'cache',
                 k_column: str = 'k',
                 v_column: str = 'v',
                 expires_column: str = 'expires') -> None:
        self._conn = connection
        self._table = table
        self._k_col = k_column
        self._v_col = v_column
        self._exp_col = expires_column

        self._ph: str

        if connection.__class__.__module__ == 'sqlite3':
            self._ph = '?'
            self._put = self._put_on_conflict  # type: ignore [assignment]
        elif connection.__class__.__module__ == 'postgresql':
            self._ph = '%s'
            self._put = self._put_on_conflict  # type: ignore [assignment]
        elif connection.__class__.__module__ == 'mysql.connector.connection':
            self._ph = '%s'
            self._put = self._put_on_duplicate_key  # type: ignore [assignment]
        else:
            self._ph = '%s'

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}('
                f'connection={self._conn!r}, '
                f'table={self._table!r}, '
                f'k_column={self._k_col!r}, '
                f'v_column={self._v_col!r}, '
                f'expires_column={self._exp_col!r})')

    def _put(self, key: Any, value: Any,
             max_age: Optional[float] = None) -> None:
        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table} '
                    f'WHERE {self._k_col} = {self._ph}',
                    (key,))
        cur.close()
        cur = self._conn.cursor()
        cur.execute(f'INSERT INTO {self._table} '
                    f'({self._k_col}, {self._v_col}, {self._exp_col}) '
                    f'VALUES ({self._ph}, {self._ph}, {self._ph})',
                    (key, self._dumps(value),
                     time.time() + max_age if max_age else None))
        cur.close()

    def _put_on_conflict(self, key: Any, value: Any,
                         max_age: Optional[float] = None) -> None:

        svalue = self._dumps(value)
        expires = time.time() + max_age if max_age else None

        cur = self._conn.cursor()
        cur.execute(f'INSERT INTO {self._table} '
                    f'({self._k_col}, {self._v_col}, {self._exp_col}) '
                    f'VALUES ({self._ph}, {self._ph}, {self._ph}) '
                    f'ON CONFLICT({self._k_col}) DO UPDATE SET '
                    f'{self._v_col} = {self._ph}, '
                    f'{self._exp_col} = {self._ph}',
                    (key, svalue, expires, svalue, expires))
        cur.close()

    def _put_on_duplicate_key(self, key: Any, value: Any,
                              max_age: Optional[float] = None) -> None:
        svalue = self._dumps(value)
        expires = time.time() + max_age if max_age else None

        cur = self._conn.cursor()
        cur.execute(f'INSERT INTO {self._table} '
                    f'({self._k_col}, {self._v_col}, {self._exp_col}) '
                    f'VALUES ({self._ph}, {self._ph}, {self._ph}) '
                    f'ON DUPLICATE KEY UPDATE '
                    f'{self._v_col} = {self._ph}, '
                    f'{self._exp_col} = {self._ph}',
                    (key, svalue, expires, svalue, expires))
        cur.close()

    def _get(self, key: Any) -> Any:
        cur = self._conn.cursor()
        cur.execute(f'SELECT {self._v_col}, {self._exp_col} '
                    f'FROM {self._table} '
                    f'WHERE {self._k_col} = {self._ph} '
                    f'AND ({self._exp_col} IS NULL '
                    f'OR {self._exp_col} > {self._ph})',
                    (key, time.time()))
        row = cur.fetchone()
        cur.close()
        if not row:
            raise KeyError(key)
        return self._loads(row[0])

    def _remove(self, key: Any) -> None:
        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table} '
                    f'WHERE {self._k_col} = {self._ph}',
                    (key,))
        rowcount = cur.rowcount
        cur.close()
        if rowcount == 0:
            raise KeyError(key)

    def remove_many(self, keys: Iterable[Any]) -> None:
        items = tuple(self._map_key(k) for k in keys)
        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table} '
                    f'WHERE {self._k_col} '
                    f'IN ({", ".join([self._ph] * len(items))})',
                    items)
        cur.close()

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

    def get_many(self, keys: Iterable[Any],
                 default: Any = ...) -> List[Tuple[Any, Any]]:

        all_keys = {self._map_key(k): k for k in keys}

        in_list = ', '.join([self._ph] * len(all_keys))
        args: List[Any] = list(all_keys.keys())
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

    def gc(self) -> None:
        cur = self._conn.cursor()
        cur.execute(f'DELETE FROM {self._table} '
                    f'WHERE {self._exp_col} <= {self._ph}',
                    (time.time(),))
        cur.close()


Cache = SqlCache
