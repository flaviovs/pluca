import unittest

from pluca.null import create


class TestNull(unittest.TestCase):

    def test_put_get(self):
        c = create()
        c.put('k1', 'v1')
        c.put('k2', 'v2')
        with self.assertRaises(KeyError):
            c.get('k1')
        with self.assertRaises(KeyError):
            c.get('k2')

    def test_get_default(self):
        c = create()
        self.assertEqual(c.get('nonexistent', 'default'), 'default')

    def test_remove(self):
        c = create()
        c.put('k', 'v')
        with self.assertRaises(KeyError):
            c.get('k')
        with self.assertRaises(KeyError):
            c.get('nonexistent')

    def test_has(self):
        c = create()
        c.put('k', 'v')
        self.assertFalse(c.has('k'))
        self.assertFalse(c.has('nonexistent'))
