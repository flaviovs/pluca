import dbm
import tempfile
import unittest
from pathlib import Path

import pluca
import pluca.dbm
from pluca.test import AdapterTester


class _TestMixin:
    _tempdir: tempfile.TemporaryDirectory  # type: ignore [type-arg]

    def _open_db(self) -> None:
        # pylint: disable-next=consider-using-with
        assert self._tempdir is not None

        self._db = dbm.open(f'{self._tempdir.name}/test', 'n')

    def tearDown(self) -> None:  # pylint: disable=invalid-name
        self._db.close()

    def get_adapter(self) -> pluca.dbm.Adapter:
        return pluca.dbm.Adapter(self._db)

    @classmethod
    def setUpClass(cls) -> None:  # pylint: disable=invalid-name
        # pylint: disable-next=consider-using-with
        cls._tempdir = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls) -> None:  # pylint: disable=invalid-name
        cls._tempdir.cleanup()


class TestDbm(_TestMixin, AdapterTester, unittest.TestCase):

    def setUp(self) -> None:
        self._open_db()

    def test_put_max_age_zero(self) -> None:
        cache = self.get_cache()
        cache.put('foo', 'bar', max_age=0)
        with self.assertRaises(KeyError):
            cache.get('foo')


class TestGeneric(unittest.TestCase):

    def test_constructor_accept_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            cache = pluca.Cache(pluca.dbm.Adapter(f'{tempdir}/db'))
            cache.put('foo', 'bar')
            self.assertEqual('bar', cache.get('foo'))

    def test_constructor_accept_path(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            cache = pluca.Cache(pluca.dbm.Adapter(Path(tempdir) / 'db'))
            cache.put('foo', 'bar')
            self.assertEqual('bar', cache.get('foo'))
