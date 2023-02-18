from pathlib import Path
from typing import Union, Optional


def create_cachedir_tag(cache_dir: Union[str, Path],
                        name: Optional[str] = 'pluca cache',
                        force: bool = False) -> None:
    if isinstance(cache_dir, str):
        cache_dir = Path(cache_dir)

    try:
        with open(cache_dir / 'CACHEDIR.TAG',
                  'w' if force else 'x',
                  encoding='utf-8') as fd:
            fd.write('Signature: 8a477f597d28d172789f06886806bc55\n'
                     '# This file is a cache directory tag '
                     f'created by {name}.')
    except FileExistsError:
        pass
