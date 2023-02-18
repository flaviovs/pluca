import tempfile
import unittest
from pathlib import Path
from types import ModuleType

import pluca
import pluca.dbm
from pluca.test import CacheTester


class _TestMixin:
    _tempdir: tempfile.TemporaryDirectory  # type: ignore [type-arg]

    def _open_db(self, module: ModuleType) -> None:
        # pylint: disable-next=consider-using-with
        assert self._tempdir is not None

        assert hasattr(module, 'open')
        self._db = module.open(  # xtype: ignore [attr-defined]
            f'{self._tempdir.name}/test', 'n')

    def tearDown(self) -> None:  # pylint: disable=invalid-name
        self._db.close()

    def get_cache(self) -> pluca.Cache:
        return pluca.dbm.Cache(self._db)

    @classmethod
    def setUpClass(cls) -> None:  # pylint: disable=invalid-name
        # pylint: disable-next=consider-using-with
        cls._tempdir = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls) -> None:  # pylint: disable=invalid-name
        cls._tempdir.cleanup()


class TestDbmGnu(_TestMixin, CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        try:
            import dbm.gnu  # pylint: disable=import-outside-toplevel
        except ImportError as ex:
            raise unittest.SkipTest(str(ex)) from ex
        self._open_db(dbm.gnu)


class TestDbmNdbm(_TestMixin, CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        try:
            import dbm.ndbm  # pylint: disable=import-outside-toplevel
        except ImportError as ex:
            raise unittest.SkipTest(str(ex)) from ex
        self._open_db(dbm.ndbm)


class TestDbmDumb(_TestMixin, CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        try:
            import dbm.dumb  # pylint: disable=import-outside-toplevel
        except ImportError as ex:
            raise unittest.SkipTest(str(ex)) from ex
        self._open_db(dbm.dumb)


class TestGeneric(unittest.TestCase):

    def test_constructor_accept_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            cache = pluca.dbm.Cache(f'{tempdir}/db')
            cache.put('foo', 'bar')
            self.assertEqual('bar', cache.get('foo'))

    def test_constructor_accept_path(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            cache = pluca.dbm.Cache(Path(tempdir) / 'db')
            cache.put('foo', 'bar')
            self.assertEqual('bar', cache.get('foo'))
