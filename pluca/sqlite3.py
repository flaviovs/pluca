import sqlite3
from typing import Mapping, Any, Union, Optional, Iterable, Tuple

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
            on the conncetion.
        **kwargs: All other arguments are passed unchanged to
            `sqlite3.connect()`.

    """

    # pylint: disable-next=too-many-arguments
    def __init__(self,
                 filename: str,
                 pragma: Optional[Mapping[str,
                                          Union[str, float, bool]]] = None,
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
            max_age: Optional[float] = None) -> None:
        super().put(key, value, max_age)
        self._commit()

    def put_many(self,
                 data: Union[Mapping[Any, Any], Iterable[Tuple[Any, Any]]],
                 max_age: Optional[float] = None) -> None:
        super().put_many(data, max_age)
        self._commit()

    def remove(self, key: Any) -> None:
        super().remove(key)
        self._commit()

    def flush(self) -> None:
        super().flush()
        self._commit()

    def gc(self) -> None:
        super().gc()
        self._commit()
        self._conn.execute('PRAGMA optimize')


Cache = SQLite3Cache
