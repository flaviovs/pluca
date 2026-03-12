import tempfile
import unittest
from pathlib import Path

import pluca
import pluca.null
import pluca.utils as plu


class TestUtils(unittest.TestCase):

    def test_create_cachedir_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plu.create_cachedir_tag(temp)
            self._assert_cache_dir_tag(Path(temp))

    def test_create_cachedir_dir_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            plu.create_cachedir_tag(temp_path)
            self._assert_cache_dir_tag(temp_path)

    def test_create_cachedir_dir_name(self) -> None:
        name = 'test xyz'
        with tempfile.TemporaryDirectory() as temp:
            plu.create_cachedir_tag(temp, name=name)
            self._assert_cache_dir_tag(Path(temp), name=name)

    def test_create_cachedir_dir_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            (temp_path / 'CACHEDIR.TAG').write_text('Not a signature',
                                                    encoding='utf-8')
            plu.create_cachedir_tag(temp_path, force=True)
            self._assert_cache_dir_tag(temp_path)

    def _assert_cache_dir_tag(self,
                              temp: Path, name: str = 'pluca cache') -> None:

        path = temp / 'CACHEDIR.TAG'
        self.assertTrue(path.is_file(), f'Not found: {path}')

        with open(path, 'r', encoding='utf-8') as fd:
            lines = fd.readlines()

        self.assertEqual(lines[0].strip(),
                         'Signature: 8a477f597d28d172789f06886806bc55')
        self.assertIn(name, lines[1])

    def test_parse_factory_path_explicit(self) -> None:
        self.assertEqual(
            plu._parse_factory_path('pluca.null:Cache'),
            ('pluca.null', 'Cache'))

    def test_parse_factory_path_default_name(self) -> None:
        self.assertEqual(
            plu._parse_factory_path('pluca.null'),
            ('pluca.null', 'Cache'))
        self.assertEqual(
            plu._parse_factory_path('pluca.null', default_name='Factory'),
            ('pluca.null', 'Factory'))

    def test_parse_factory_path_module_with_dots(self) -> None:
        self.assertEqual(
            plu._parse_factory_path('pluca_memcache.Cache'),
            ('pluca_memcache.Cache', 'Cache'))

    def test_parse_factory_path_invalid(self) -> None:
        invalid = (':Cache', 'pluca.null:', 'a:b:c')
        for path in invalid:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    plu._parse_factory_path(path)

    def test_create_cache_module_defaults_to_cache(self) -> None:
        cache = plu.create_cache('pluca.null')
        self.assertIsInstance(cache, pluca.Cache)
        self.assertIsInstance(cache, pluca.null.Cache)

    def test_create_cache_explicit_factory(self) -> None:
        cache = plu.create_cache('pluca.null:Cache')
        self.assertIsInstance(cache, pluca.null.Cache)
