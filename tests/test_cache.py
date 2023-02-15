import sys
import unittest
import tempfile

import pluca.file
import pluca.null
import pluca.memory
import pluca.cache as plc


class TestCache(unittest.TestCase):

    def setUp(self) -> None:
        plc.remove_all()
        # Make sure that pluca module used in the tests are unloaded
        # before tests.
        for mod in ('pluca.file', 'pluca.memory', 'pluca.null'):
            try:
                del sys.modules[mod]
            except KeyError:
                pass

    def test_add_get(self) -> None:
        plc.add('', 'file')
        plc.add('mod', 'null')
        plc.add('pkg.mod', 'memory')

        cache = plc.get_cache('')
        self.assertIsInstance(cache, pluca.file.Cache)

        cache = plc.get_cache('non-existent')
        self.assertIsInstance(cache, pluca.file.Cache)

        cache = plc.get_cache('mod')
        self.assertIsInstance(cache, pluca.null.Cache)

        cache = plc.get_cache('pkg.mod')
        self.assertIsInstance(cache, pluca.memory.Cache)

    def test_add_get_child(self) -> None:
        plc.add('', 'file')
        plc.add('pkg', 'memory')
        plc.add('pkg.mod', 'null')
        cache = plc.get_child('pkg', 'mod')
        self.assertIsInstance(cache, pluca.null.Cache)

    def test_add_no_root(self) -> None:
        plc.add('mod', 'null')
        cache = plc.get_cache('mod')
        self.assertIsInstance(cache, pluca.null.Cache)
        cache = plc.get_cache('nonexistend')
        self.assertIsInstance(cache, pluca.file.Cache)

    def test_add_reuse(self) -> None:
        plc.add('', 'file')
        plc.add('mod', 'file')

        root_cache = plc.get_cache('')
        mod_cache = plc.get_cache('mod')
        self.assertIs(root_cache, mod_cache)

    def test_add_no_reuse(self) -> None:
        plc.add('', 'file')
        plc.add('mod', 'file', reuse=False)

        root_cache = plc.get_cache('')
        mod_cache = plc.get_cache('mod')
        self.assertIsNot(root_cache, mod_cache)

    def test_add_no_implicit_reuse(self) -> None:
        plc.add('foo', 'file', name='foo')
        plc.add('bar', 'file', name='bar')
        self.assertIsNot(plc.get_cache('foo'), plc.get_cache('bar'))

    def test_add_dup_name(self) -> None:
        plc.add('name', 'null')
        with self.assertRaises(ValueError):
            plc.add('name', 'memory')

    def test_basic_config(self) -> None:
        plc.basic_config()

        cache = plc.get_cache('')
        self.assertIsInstance(cache, pluca.file.Cache)

    def test_basic_config_called_explicitly(self) -> None:
        cache = plc.get_cache('')
        self.assertIsInstance(cache, pluca.file.Cache)

    def test_remove(self) -> None:
        plc.add('', 'file')
        plc.add('mod', 'null')
        plc.remove('mod')

        cache = plc.get_cache('mod')
        self.assertIsInstance(cache, pluca.file.Cache)

    def test_remove_root(self) -> None:
        plc.add('', 'file')

        plc.remove('')

        cache = plc.get_cache('mod')
        self.assertIsInstance(cache, pluca.file.Cache)

    def test_remove_raises_keyerror(self) -> None:
        with self.assertRaises(KeyError) as ctx:
            plc.remove('mod')
        self.assertEqual(ctx.exception.args, ('mod',))

    def test_remove_all(self) -> None:
        plc.add('', 'null')
        plc.add('mod', 'null')
        plc.add('pkg.mod', 'null')

        plc.remove_all()

        self.assertIsInstance(plc.get_cache('pkg.mod'), pluca.file.Cache)
        self.assertIsInstance(plc.get_cache('mod'), pluca.file.Cache)
        self.assertIsInstance(plc.get_cache(''), pluca.file.Cache)

    def test_dict_config(self) -> None:
        plc.dict_config({
            'class': 'file',
            'caches': {
                'mod': {
                    'class': 'null',
                },
                'pkg.mod': {
                    'class': 'memory',
                    'max_entries': 10,
                },
            },
        })

        cache = plc.get_cache('')
        self.assertIsInstance(cache, pluca.file.Cache)

        cache = plc.get_cache('non-existent')
        self.assertIsInstance(cache, pluca.file.Cache)

        cache = plc.get_cache('mod')
        self.assertIsInstance(cache, pluca.null.Cache)

        cache = plc.get_cache('pkg.mod')
        self.assertIsInstance(cache, pluca.memory.Cache)

    def test_reconfig_basic(self) -> None:
        plc.basic_config('file')
        plc.basic_config('null')
        cache = plc.get_cache('foo')
        self.assertIsInstance(cache, pluca.null.Cache)

    def test_reconfig_dict_config(self) -> None:
        plc.dict_config({'class': 'file'})
        plc.dict_config({'class': 'null'})
        cache = plc.get_cache('foo')
        self.assertIsInstance(cache, pluca.null.Cache)

    def test_file_config(self) -> None:
        # pylint: disable-next=consider-using-with
        temp = tempfile.NamedTemporaryFile(mode='w+', suffix='.ini')
        temp.write('''
        [__root__]
        class = file

        [mod]
        class = null

        [pkg.mod]
        class = memory
        max_entries = 100
        ''')
        temp.flush()
        temp.seek(0)

        plc.file_config(temp.name)

        cache = plc.get_cache('')
        self.assertIsInstance(cache, pluca.file.Cache)

        cache = plc.get_cache('non-existent')
        self.assertIsInstance(cache, pluca.file.Cache)

        cache = plc.get_cache('mod')
        self.assertIsInstance(cache, pluca.null.Cache)

        cache = plc.get_cache('pkg.mod')
        self.assertIsInstance(cache, pluca.memory.Cache)
