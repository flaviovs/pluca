import unittest
import tempfile

from pluca import StdPickleMixin


class TestStdPickleMixin(unittest.TestCase):

    def test_loads(self):
        obj = StdPickleMixin()

        data = (1, 3.1415, False, None, {'a': 1}, (7, 8, 9), {10, 20})

        self.assertEqual(obj._loads(obj._dumps(data)), data)

    def test_load(self):
        obj = StdPickleMixin()

        data = (1, 3.1415, False, None, {'a': 1}, (7, 8, 9), {10, 20})

        with tempfile.TemporaryFile() as fd:
            obj._dump(fd, data)
            fd.seek(0)
            self.assertEqual(obj._load(fd), data)
