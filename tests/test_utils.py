import tempfile
import unittest
from pathlib import Path

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
        self.assertTrue(path.is_file, f'Not found: {path}')

        with open(path, 'r', encoding='utf-8') as fd:
            lines = fd.readlines()

        self.assertEqual(lines[0].strip(),
                         'Signature: 8a477f597d28d172789f06886806bc55')
        self.assertIn(name, lines[1])
