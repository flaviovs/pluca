import tempfile
import unittest

import pluca
import pluca.dbm
from pluca.test import CacheTester


class TestDbmGnu(CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        try:
            import dbm.gnu  # pylint: disable=import-outside-toplevel
        except ImportError as ex:
            raise unittest.SkipTest(str(ex)) from ex

        # pylint: disable-next=consider-using-with
        temp = tempfile.NamedTemporaryFile()
        self._db = dbm.gnu.open(temp.name, 'n')

    def tearDown(self) -> None:
        self._db.close()

    def get_cache(self) -> pluca.Cache:
        return pluca.dbm.Cache(self._db)


class TestDbmNdbm(CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        try:
            import dbm.ndbm  # pylint: disable=import-outside-toplevel
        except ImportError as ex:
            raise unittest.SkipTest(str(ex)) from ex

        # pylint: disable-next=consider-using-with
        temp = tempfile.NamedTemporaryFile()
        self._db = dbm.ndbm.open(temp.name, 'n')

    def tearDown(self) -> None:
        self._db.close()

    def get_cache(self) -> pluca.Cache:
        return pluca.dbm.Cache(self._db)


class TestDbmDumb(CacheTester, unittest.TestCase):

    def setUp(self) -> None:
        try:
            import dbm.dumb  # pylint: disable=import-outside-toplevel
        except ImportError as ex:
            raise unittest.SkipTest(str(ex)) from ex

        # pylint: disable-next=consider-using-with
        temp = tempfile.NamedTemporaryFile()
        self._db = dbm.dumb.open(temp.name, 'n')

    def tearDown(self) -> None:
        self._db.close()

    def get_cache(self) -> pluca.Cache:
        return pluca.dbm.Cache(self._db)
