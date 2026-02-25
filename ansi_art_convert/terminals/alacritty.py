from __future__ import annotations
from dataclasses import dataclass
import os
import subprocess
import tomlkit
from importlib.resources import files

def get_config_path() -> str:
    'Path to the alacritty.toml config file in the package resources.'
    return str(files('ansi_art_convert.terminals.configs').joinpath('alacritty.toml'))

CONFIG_FPATH = get_config_path()

FONT_OFFSETS = {
    'Amiga Topaz 1':      {},
    'Amiga Topaz 1+':     {},
    'Amiga Topaz 2':      {},
    'Amiga Topaz 2+':     {},
    'Amiga MicroKnight':  {},
    'Amiga MicroKnight+': {},
    'Amiga mOsOul':       {},
    'Amiga P0T-NOoDLE':   {},
    'IBM VGA':            {'x': -2},
}

@dataclass
class AlacrittyClient:
    config: dict

    def __init__(self, config_fpath: str = CONFIG_FPATH) -> None:
        with open(config_fpath, 'r') as f:
            self.config = tomlkit.loads(f.read())

    def launch(self) -> None:
        with open(CONFIG_FPATH, 'w') as f:
            f.write(tomlkit.dumps(self.config))

        env = os.environ.copy()
        env['ALACRITTY_CONFIG'] = CONFIG_FPATH

        subprocess.run(['alacritty', '--config-file', CONFIG_FPATH, '-v'], env=env)

    @staticmethod
    def session_is_custom_alacritty() -> bool:
        return os.environ.get('ALACRITTY_CONFIG', '') == CONFIG_FPATH

    def with_font(self, font_name: str) -> AlacrittyClient:
        offset = FONT_OFFSETS.get(font_name, {})
        offset_x, offset_y = offset.get('x', 0), offset.get('y', 0)

        self.config['font']['offset'] = {'x': offset_x, 'y': offset_y}

        return self

    def update_config(self) -> None:
        with open(CONFIG_FPATH, 'w') as f:
            f.write(tomlkit.dumps(self.config))