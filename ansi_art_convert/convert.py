#!/usr/bin/env python3

from __future__ import annotations
from argparse import ArgumentParser
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from itertools import batched
import os
import pprint
import sys
from typing import Iterator, NamedTuple, Tuple

from laser_prynter import pp

from ansi_art_convert.encoding import detect_encoding, SupportedEncoding
from ansi_art_convert.font_data import FONT_DATA, FILE_DATA_TYPES, UNICODE_TO_CP437
from ansi_art_convert.log import dprint, DEBUG

@dataclass
class ANSIToken:
    value:          str
    value_name:     str  = field(default='')
    value_map:      dict = field(repr=False, default_factory=dict)
    original_value: str  = field(init=False)

    def __post_init__(self):
        self.original_value = self.value
        self.value_name = self.value_map.get(self.value, '')

    def repr(self):
        return '\n'.join([
            f'\x1b[37m{self.__class__.__name__:<20}\x1b[0m'
            + '  {title:<s} {value!r:<4}'.format(title='value:', value=self.value)
            + '  {title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
        ])

    def __str__(self):
        return self.value


@staticmethod
def get_glyph_offset(font_name: str) -> int:
    if  'topaz' in font_name.lower():
        if '1' in font_name:
            offset = 0xE000
        elif '2' in font_name:
            offset = 0xE100
        else:
            raise ValueError(f'Unknown Topaz font_name {font_name!r}')
    elif 'mosoul' in font_name.lower():
        offset = 0xE200
    elif 'microknight' in font_name.lower():
        offset = 0xE300
    elif 'noodle' in font_name.lower():
        offset = 0xE400
    elif 'ibm' in font_name.lower():
        offset = 0xE500
    else:
        raise ValueError(f'Unknown font_name: {font_name!r}')
    dprint(f'font_name: {font_name!r} -> offset: {hex(offset)}')
    return offset


@dataclass
class TextToken(ANSIToken):
    offset: int = 0xE100
    hex_values: list[str] = field(default_factory=list, repr=False)

    def __post_init__(self):
        super().__post_init__()
        new_values = []
        for v in self.value:
            if DEBUG:
                self.hex_values.append(str(hex(ord(v))))
            if ord(v) <= 255: # and not (0x21 <= ord(v) <= 0x7e):
                new_values.append(chr(ord(v)+self.offset))
            else:
                new_values.append(v)
        self.value = ''.join(new_values)

    def repr(self):
        return '\n'.join([
            f'\x1b[32m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<17s} {value!r}'.format(title='original:', value=self.original_value),
            '  {title:<17s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<17s} {value!r}'.format(title='hex_values:', value=self.hex_values),
            '  {title:<17s} {value!r}'.format(title='len:', value=len(self.value)),
        ])

C0_TOKEN_NAMES = {
    0x00: 'NUL', 0x01: 'SOH', 0x02: 'STX', 0x03: 'ETX', 0x04: 'EOT', 0x05: 'ENQ', 0x06: 'ACK', 0x07: 'BEL',
    0x08: 'BS',  0x09: 'HT',  0x0A: 'LF',  0x0B: 'VT',  0x0C: 'FF',  0x0D: 'CR',  0x0E: 'SO',  0x0F: 'SI',
    0x10: 'DLE', 0x11: 'DC1', 0x12: 'DC2', 0x13: 'DC3', 0x14: 'DC4', 0x15: 'NAK', 0x16: 'SYN', 0x17: 'ETB',
    0x18: 'CAN', 0x19: 'EM',  0x1A: 'SUB', 0x1B: 'ESC', 0x1C: 'FS',  0x1D: 'GS',  0x1E: 'RS',  0x1F: 'US',
}

@dataclass
class C0Token(TextToken):
    value_map: dict = field(repr=False, default_factory=lambda: C0_TOKEN_NAMES)

    def __post_init__(self):
        super().__post_init__()
        self.value_name = self.value_map.get(ord(self.original_value), '')
        if self.value_name == 'CR':
            self.value = ''

    def repr(self):
        return '\n'.join([
            f'\x1b[33m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r:<6}'.format(title='value:', value=self.value)
            + '{title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
            + '{title:<10s} {value!r:<6}'.format(title='original:', value=self.original_value)
            + '{title:<4s} {value!r}'.format(title='len:', value=len(self.value))
        ])

CP_437_MAP = {
    0x01: '☺', 0x02: '☻', 0x03: '♥', 0x04: '♦', 0x05: '♣', 0x06: '♠', 0x07: '•', 0x08: '◘',
    0x09: '○', 0x0A: '◙', 0x0B: '♂', 0x0C: '♀', 0x0D: '♪', 0x0E: '♫', 0x0F: '☼', 0x10: '►',
    0x11: '◄', 0x12: '↕', 0x13: '‼', 0x14: '¶', 0x15: '§', 0x16: '▬', 0x17: '↨', 0x18: '↑',
    0x19: '↓', 0x1A: '→', 0x1B: '←', 0x1C: '∟', 0x1D: '↔', 0x1E: '▲', 0x1F: '▼',
}


@dataclass
class CP437Token(ANSIToken):
    offset: int = 0xE100
    hex_values: list[str] = field(default_factory=list, repr=False)

    def _translate_char(self, ch: str) -> str:
        n = UNICODE_TO_CP437.get(ord(ch), ord(ch))
        if n <= 255:
            return chr(n + self.offset)
        else:
            return ch

    def __post_init__(self):
        super().__post_init__()
        if DEBUG:
            for v in self.original_value:
                self.hex_values.append(str(hex(ord(v))))
        self.value = ''.join([self._translate_char(v) for v in self.original_value])
        self.value_name = self.value_map.get(self.original_value, '')

    def repr(self):
        return '\n'.join([
            f'\x1b[32m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<17s} {value!r}'.format(title='original:', value=self.original_value),
            '  {title:<17s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<17s} {value!r}'.format(title='hex_values:', value=self.hex_values),
            '  {title:<17s} {value!r}'.format(title='len:', value=len(self.value)),
        ])


ANSI_CONTROL_CODES = {
    'A': 'CursorUp',
    'B': 'CursorDown',
    'C': 'CursorForward',
    'D': 'CursorBackward',
    'E': 'CursorNextLine',
    'F': 'CursorPrevLine',
    'G': 'CursorHorizontalAbsolute',
    'H': 'CursorPosition',
    'J': 'EraseInDisplay',
    'K': 'EraseInLine',
    'S': 'ScrollUp',
    'T': 'ScrollDown',
    'f': 'CursorPosition',
    's': 'SaveCursorPosition',
    'u': 'RestoreCursorPosition',
}

@dataclass
class ControlToken(ANSIToken):
    value_map: dict = field(repr=False, default_factory=lambda: ANSI_CONTROL_CODES)
    subtype: str = field(init=False)

    def __post_init__(self):
        self.subtype = self.value[-1]
        self.value_name = self.value_map.get(self.subtype, '')
        super().__post_init__()

    def repr(self):
        lines = (
            f'\x1b[35m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r:<6}'.format(title='value:', value=self.value)
            + '{title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
            + '{title:<10s} {value!r}'.format(title='subtype:', value=self.subtype)
        )
        if self.subtype == 'C':
            lines += '  {title:<20s} {value!r}'.format(title='spaces:', value=' '*int(self.value[:-1]))
        return lines

    def __str__(self):
        if self.subtype == 'C':
            return ' '*int(self.value[:-1] or '1')
        elif self.subtype == 'H':
            return '\n'
        else:
            return ''

class ColourType(Enum):
    FG = 'fg'
    BG = 'bg'

@dataclass
class ColorFGToken(ANSIToken):
    pass

@dataclass
class ColorBGToken(ANSIToken):
    pass

@dataclass
class TrueColorFGToken(ColorFGToken):
    colour_type: ColourType = field(repr=False, default=ColourType.FG)
    def __str__(self):
        r, g, b = self.value.split(',')
        return f'\x1b[38;2;{r};{g};{b}m'
    def repr(self):
        return '\n'.join([
            f'\x1b[94m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<20s} {value!r}'.format(title='colour_type:', value=self.colour_type.value),
        ])

@dataclass
class TrueColorBGToken(ColorBGToken):
    colour_type: ColourType = field(repr=False, default=ColourType.BG)
    def __str__(self):
        r, g, b = self.value.split(',')
        return f'\x1b[48;2;{r};{g};{b}m'
    def repr(self):
        return '\n'.join([
            f'\x1b[96m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<20s} {value!r}'.format(title='colour_type:', value=self.colour_type.value),
        ])

@dataclass
class Color256FGToken(ColorFGToken):
    colour_type: ColourType = field(repr=False, default=ColourType.FG)
    def __str__(self):
        n = self.value
        return f'\x1b[38;5;{n}m'
    def repr(self):
        return '\n'.join([
            f'\x1b[34m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<20s} {value!r}'.format(title='colour_type:', value=self.colour_type.value),
        ])

@dataclass
class Color256BGToken(ColorBGToken):
    colour_type: ColourType = field(repr=False, default=ColourType.BG)
    def __str__(self):
        n = self.value
        return f'\x1b[48;5;{n}m'
    def repr(self):
        return '\n'.join([
            f'\x1b[36m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<20s} {value!r}'.format(title='colour_type:', value=self.colour_type.value),
        ])

COLOUR_8_FG_VALUES = {
    '30': 'black', '31': 'red', '32': 'green', '33': 'yellow',
    '34': 'blue', '35': 'magenta', '36': 'cyan', '37': 'white',
}
COLOUR_8_FG_BRIGHT_VALUES = {
    '90': 'bright_black', '91': 'bright_red', '92': 'bright_green', '93': 'bright_yellow',
    '94': 'bright_blue', '95': 'bright_magenta', '96': 'bright_cyan', '97': 'bright_white',
}
COLOUR_8_BG_VALUES = {
    '40': 'black', '41': 'red', '42': 'green', '43': 'yellow',
    '44': 'blue', '45': 'magenta', '46': 'cyan', '47': 'white',
}
COLOUR_8_BG_BRIGHT_VALUES = {
    '100': 'bright_black', '101': 'bright_red', '102': 'bright_green', '103': 'bright_yellow',
    '104': 'bright_blue', '105': 'bright_magenta', '106': 'bright_cyan', '107': 'bright_white',
}
COLOUR_8_FG_VALUES = COLOUR_8_FG_VALUES | COLOUR_8_FG_BRIGHT_VALUES
COLOUR_8_BG_VALUES = COLOUR_8_BG_VALUES | COLOUR_8_BG_BRIGHT_VALUES
COLOUR_8_VALUES = COLOUR_8_FG_VALUES | COLOUR_8_BG_VALUES

@dataclass
class Color8Token(ANSIToken):
    params:      list[str]            = field(default_factory=list)
    ice_colours: bool                 = field(repr=False, default=False)
    bright_bg:   bool                  = field(init=False, default=False)
    bright_fg:   bool                 = field(init=False, default=False)
    sgr_tokens:  list[SGRToken]      = field(init=False, default_factory=list)
    fg_token:    Color8FGToken | None = field(init=False, default=None)
    bg_token:    Color8BGToken | None = field(init=False, default=None)
    tokens:      list[ANSIToken]      = field(init=False, default_factory=list)

    def __post_init__(self):
        for param in self.params:
            if param in SGR_CODES:
                if self.ice_colours and param == '5':
                    self.bright_bg = True
                    continue
                elif param == '1':
                    self.bright_fg = True
                t = SGRToken(value=param)
                self.sgr_tokens.append(t)
                self.tokens.append(t)
            elif param in COLOUR_8_FG_VALUES:
                self.fg_token = Color8FGToken(value=param, bright=self.bright_fg)
                self.tokens.append(self.fg_token)
            elif param in COLOUR_8_BG_VALUES:
                ice_colours = self.ice_colours and self.bright_bg
                self.bg_token = Color8BGToken(value=param, ice_colours=ice_colours)
                self.tokens.append(self.bg_token)

    def generate_tokens(self, curr_fg: ColorFGToken | None, curr_bg: ColorBGToken | None) -> Iterator[ANSIToken]:
        if self.sgr_tokens:
            if SGRToken(value='0') in self.sgr_tokens:
                curr_fg = Color8FGToken(value='37', bright=self.bright_fg)
                curr_bg = Color8BGToken(value='40', ice_colours=self.bright_bg)
            yield from self.sgr_tokens
        if self.fg_token:
            yield self.fg_token
        else:
            if curr_fg is None:
                yield Color8FGToken(value='37', bright=self.bright_fg)
            elif isinstance(curr_fg, Color8FGToken):
                yield Color8FGToken(value=curr_fg.original_value, bright=self.bright_fg)

        bright_bg = False
        if self.bg_token and isinstance(self.bg_token, Color8BGToken) and self.bg_token.ice_colours:
            bright_bg = True
        if curr_bg and isinstance(curr_bg, Color8BGToken) and curr_bg.ice_colours:
            bright_bg = True
        if self.bright_bg:
            bright_bg = True

        if self.bg_token:
            yield Color8BGToken(value=self.bg_token.original_value, ice_colours=bright_bg)
        else:
            if curr_bg is None:
                yield Color8BGToken(value='40', ice_colours=bright_bg)
            elif isinstance(curr_bg, Color8BGToken):
                yield Color8BGToken(value=curr_bg.original_value, ice_colours=bright_bg)

    def __str__(self):
        return f'\x1b[{self.value}m'

    def repr(self):
        lines = [
            f'\x1b[93m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<20s} {value!r}'.format(title='params:', value=self.params),
            '  {title:<20s} {value!r}'.format(title='ice_colours:', value=self.ice_colours),
        ]
        for t in self.tokens:
            lines.append('\n'.join(['  ' + line for line in t.repr().split('\n')]))
        return '\n'.join(lines)
    
@dataclass
class Color8FGToken(ColorFGToken):
    value_map: dict = field(repr=False, default_factory=lambda: COLOUR_8_FG_VALUES)
    colour_type: ColourType = field(repr=False, default=ColourType.FG)
    bright: bool = False

    def __post_init__(self):
        super().__post_init__()
        if self.bright:
            base_value = int(self.value)
            if base_value < 90:
                self.value = str(base_value + 60)

    def repr(self):
        return '\n'.join([
            f'\x1b[96m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r:<6}'.format(title='value:', value=self.value)
            + '{title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
            + '{title:<10s} {value!r:<6}'.format(title='original:', value=self.original_value)
        ])

    def __str__(self):
        return f'\x1b[{self.value}m'

@dataclass
class Color8BGToken(ColorBGToken):
    value_map: dict = field(repr=False, default_factory=lambda: COLOUR_8_BG_VALUES)
    colour_type: ColourType = field(repr=False, default=ColourType.BG)
    ice_colours: bool = field(default=False)

    def __post_init__(self):
        super().__post_init__()
        self.original_value = self.value
        if self.ice_colours:
            self.value = str(int(self.value) + 60)

    def repr(self):
        return '\n'.join([
            f'\x1b[94m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r:<6}'.format(title='value:', value=self.value)
            + '{title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
            + '{title:<10s} {value!r:<6}'.format(title='original:', value=self.original_value)
            + '{title:<12s} {value!r}'.format(title='ice_colours:', value=self.ice_colours)
        ])

    def __str__(self):
        return f'\x1b[{self.value}m'

SGR_CODES = {
    '0':  'Reset', '1':  'Bold', '2':  'Dim', '3':  'Italic', '4':  'Underline', '5':  'BlinkSlow',
    '6':  'BlinkRapid', '7':  'ReverseVideo', '8':  'Conceal', '9':  'CrossedOut',
}

@dataclass
class SGRToken(ANSIToken):
    value_map: dict = field(repr=False, default_factory=lambda: SGR_CODES)
    def __str__(self):
        return f'\x1b[{self.value}m'
    def repr(self):
        return '\n'.join([
            f'\x1b[95m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r:<6}'.format(title='value:', value=self.value)
            + '{title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
        ])

@dataclass
class NewLineToken(ANSIToken):
    def __str__(self):
        return '\n'

    def repr(self):
        return '\n'.join([
            f'\x1b[93m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r}'.format(title='value:', value=self.value),
        ])

@dataclass
class EOFToken(ANSIToken):
    def __str__(self):
        return ''
    def repr(self):
        return '\n'.join([
            f'\x1b[90m{self.__class__.__name__:<20}\x1b[0m'
            + '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
        ])

@dataclass
class UnknownToken(ANSIToken):
    def repr(self):
        return '\n'.join([
            f'\x1b[91m{self.__class__.__name__:<20}\x1b[0m'
            + '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
        ])

ASPECT_RATIO_MAP = {
    (0, 0): 'Legacy value. No preference.',
    (0, 1): 'Image was created for a legacy device. When displayed on a device with square pixels, either the font or the image needs to be stretched.',
    (1, 0): 'Image was created for a modern device with square pixels. No stretching is desired on a device with square pixels.',
    (1, 1): 'Not currently a valid value.'
}
LETTER_SPACING_MAP = {
    (0, 0): 'Legacy value. No preference.',
    (0, 1): 'Select 8 pixel font.',
    (1, 0): 'Select 9 pixel font.',
    (1, 1): 'Not currently a valid value.'
}
TINFO_NAMES = ['tinfo1', 'tinfo2', 'tinfo3', 'tinfo4']

class SauceRecordExtended(NamedTuple):
    'extended sauce record with extra fields for interpreted/expanded comments, font & flag descriptions'
    fpath:          str
    encoding:       SupportedEncoding
    sauce:          SauceRecord
    comments_data:  list[str]
    font:           dict
    tinfo:          dict
    aspect_ratio:   dict = field(init=False, repr=False)
    letter_spacing: dict = field(init=False, repr=False)
    flags:          dict = field(repr=False, default_factory=dict)
    ice_colours:    bool = field(default=False)

    @staticmethod
    def parse_comments(comment_block: str, n_comments: int) -> list[str]:
        dprint(f'Parsing {n_comments} comments from comment block of size {len(comment_block)}')
        if len(comment_block) != (n_comments * 64) + 5:
            raise ValueError(f'Invalid comment block size: expected {n_comments * 64 + 5}, got {len(comment_block)}')
        dprint(f'Comment block raw data: {comment_block=!r}')

        comments_data = []
        for c in map(''.join, batched(comment_block[5:], 64)):
            comments_data.append(c.rstrip('\x00'))

        return comments_data

    @staticmethod
    def parse_flags(raw_n: int) -> dict:
        f = list(map(int, f'{raw_n:08b}'))
        dprint(f'Parsing flags from raw value {raw_n}: bits={f}')
        _bit1, _bit2, _bit3, ar1, ar2, ls1, ls2, b = f

        return {
            'aspect_ratio':   ASPECT_RATIO_MAP.get((ar1, ar2), 'Unknown'),
            'letter_spacing': LETTER_SPACING_MAP.get((ls1, ls2), 'Unknown'),
            'non_blink_mode': bool(b),
        }

    @staticmethod
    def parse_font(font_name: str) -> dict:
        dprint(f'Parsing font data for font name: {font_name!r}')
        return FONT_DATA.get(font_name, {})

    @staticmethod
    def parse_tinfo_field(tinfo_key: str, sauce: SauceRecord) -> dict:
        if sauce.data_type == 5:
            # ('BinaryText', 'Variable'): {'tinfo1': '0', 'tinfo2': '0', 'tinfo3': '0', 'tinfo4': '0' }``
            raise NotImplementedError('SAUCE tinfo parsing for data_type 5 (BinaryText) is not implemented.')
        return {
            'name':  FILE_DATA_TYPES.get((sauce.data_type, sauce.file_type), {}).get(tinfo_key, '0'),
            'value': getattr(sauce, tinfo_key),
        }

    @staticmethod
    def parse_tinfo(sauce: SauceRecord) -> dict:
        info = {}
        for name in TINFO_NAMES:
            field_info = SauceRecordExtended.parse_tinfo_field(name, sauce)
            if field_info['name'] != '0':
                info[name] = field_info
        return info

    @staticmethod
    def parse(sauce: SauceRecord, file_data: str, fpath: str, encoding: SupportedEncoding) -> Tuple[SauceRecordExtended, str]:
        flags = SauceRecordExtended.parse_flags(sauce.flags)
        font = SauceRecordExtended.parse_font(sauce.tinfo_s.strip())
        tinfo = SauceRecordExtended.parse_tinfo(sauce)
        ice_colours = flags.get('non_blink_mode', False)

        kwargs = {
            'fpath':         fpath,
            'encoding':      encoding,
            'sauce':         sauce,
            'comments_data': [],
            'flags':         flags,
            'font':          font,
            'tinfo':         tinfo,
            'ice_colours':   ice_colours,
        }
        if sauce.comments == 0:
            dprint('No comments present in SAUCE record.')
            return SauceRecordExtended(**kwargs), file_data

        blockIdx = len(file_data)-(sauce.comments*64)+5
        data, comment_block = file_data[:blockIdx], file_data[blockIdx:]

        dprint(f'comment block: {comment_block!r}')

        try:
            comments_data = SauceRecordExtended.parse_comments(comment_block, sauce.comments)

            return SauceRecordExtended(**(kwargs | {'comments_data': comments_data})), data
        except ValueError as ve:
            dprint(f'Error parsing comments: {ve}')
            return SauceRecordExtended(**kwargs), file_data

    def asdict(self) -> dict:
        return {
            'sauce': self.sauce._asdict(),
            'extended': {
                'file_name':   os.path.basename(self.fpath),
                'encoding':    self.encoding.value,
                'comments':    self.comments_data,
                'tinfo':       self.tinfo,
                'flags':       self.flags,
                'font':        self.font,
                'ice_colours': self.ice_colours,
            }
        }


class SauceRecord(NamedTuple):
    ID:        str = '' #   5b
    version:   str = '' # + 2b  = 7b
    title:     str = '' # + 35b = 42b
    author:    str = '' # + 20b = 62b
    group:     str = '' # + 20b = 82b
    date:      str = '' # + 8b  = 90b
    filesize:  int = 0  # + 4b  = 94b
    data_type: int = 0  # + 1b  = 95b
    file_type: int = 0  # + 1b  = 96b
    tinfo1:    int = 0  # + 2b  = 98b
    tinfo2:    int = 0  # + 2b  = 100b
    tinfo3:    int = 0  # + 2b  = 102b
    tinfo4:    int = 0  # + 2b  = 104b
    comments:  int = 0  # + 1b  = 105b
    flags:     int = 0  # + 1b  = 106b
    tinfo_s:   str = '' # + 22b = 128b

    @staticmethod
    def offsets():
        return {
            'ID':        (0, 5),
            'version':   (5, 7),
            'title':     (7, 42),
            'author':    (42, 62),
            'group':     (62, 82),
            'date':      (82, 90),
            'filesize':  (90, 94),
            'data_type': (94, 95),
            'file_type': (95, 96),
            'tinfo1':    (96, 98),
            'tinfo2':    (98, 100),
            'tinfo3':    (100, 102),
            'tinfo4':    (102, 104),
            'comments':  (104, 105),
            'flags':     (105, 106),
            'tinfo_s':   (106, 128),
        }

    def is_empty(self) -> bool:
        return self.ID != 'SAUCE'

    @staticmethod
    def parse_field(key: str, raw_value: bytes, encoding: str):
        if key in {'data_type', 'file_type', 'comments', 'filesize', 'tinfo1', 'tinfo2', 'tinfo3', 'tinfo4', 'flags'}:
            dprint(f'Parsing {key} field with raw value: {raw_value!r}')
            return int.from_bytes(raw_value.rstrip(b'\x00'), byteorder='little', signed=False)
        else:
            dprint(f'Parsing {key} field with raw value: {raw_value.replace(b"\x00", b"").strip()!r}')
            return raw_value.replace(b'\x00', b'').strip().decode(encoding)

    @staticmethod
    def parse_record(file_data: bytes, encoding) -> Tuple[SauceRecord, str]:
        data, sauce_data = file_data[:-128], file_data[-128:]

        if not (sauce_data and sauce_data.startswith(b'SAUCE')):
            dprint(f'No SAUCE record found: {sauce_data[:5]!r}')
            return SauceRecord(), file_data.decode(encoding)

        values = {}
        for key, (start, end) in SauceRecord.offsets().items():
            values[key] = SauceRecord.parse_field(key, sauce_data[start:end], encoding)

        return SauceRecord(*values.values()), data.decode(encoding)


@dataclass
class Tokeniser:
    fpath:        str
    sauce:        SauceRecordExtended
    data:         str
    font_name:    str
    encoding:     SupportedEncoding   = SupportedEncoding.CP437
    tokens:       list[ANSIToken]     = field(default_factory=list, init=False)
    glyph_offset: int                 = field(init=False, default=0)
    ice_colours:  bool                = field(default=False)
    width:        int                 = field(default=0)
    counts:       Counter[tuple[str, str]] = field(default_factory=Counter, init=False)
    _textTokenType: type = field(init=False, repr=False, default=TextToken)

    def __post_init__(self):
        if self.font_name:
            self.glyph_offset = get_glyph_offset(self.font_name)
        elif 'name' in self.sauce.font:
            self.glyph_offset = get_glyph_offset(self.sauce.font['name'])
        else:
            if self.encoding == SupportedEncoding.CP437:
                self.glyph_offset = get_glyph_offset('ibm')

        if not self.width:
            self.width = int(self.sauce.sauce.tinfo1) or 80

        if not self.ice_colours:
            self.ice_colours = self.sauce.flags['non_blink_mode']

        if self.encoding == SupportedEncoding.CP437:
            self._textTokenType = CP437Token
        else:
            self._textTokenType = TextToken

        dprint(f'Using extended sauce: {self.sauce!r}')
        dprint(f'Width: {self.width}, Glyph offset: {hex(self.glyph_offset)}, Ice colours: {self.ice_colours}')

    def create_tokens(self, code_chars: list[str]) -> list[ANSIToken]:
        'Create a token from a complete ANSI escape sequence.'
        if len(code_chars) < 3:
            return [UnknownToken(value=''.join(code_chars))]

        # Handle custom true color format: \x1b[0;R;G;Bt (FG) or \x1b[1;R;G;Bt (BG)
        if code_chars[0:2] == ['\x1b', '['] and code_chars[-1] == 't':
            params = ''.join(code_chars[2:-1]).split(';')
            if len(params) == 4 and params[0] in ['0', '1']:
                mode, r, g, b = params
                rgb_value = f'{int(r)},{int(g)},{int(b)}'
                if mode == '0':
                    return [TrueColorBGToken(value=rgb_value)]
                elif mode == '1':
                    return [TrueColorFGToken(value=rgb_value)]

        if code_chars[0:2] == ['\x1b', '['] and code_chars[-1] == 'm':
            params = ''.join(code_chars[2:-1]).split(';')
            return [Color8Token(value=';'.join(params), params=params, ice_colours=self.ice_colours)]

        elif code_chars[-1] in ANSI_CONTROL_CODES:
            return [ControlToken(value=''.join(code_chars[2:]))]

        return [UnknownToken(value=''.join(code_chars))]

    def tokenise(self) -> Iterator[ANSIToken]:
        'Tokenise ANSI escape sequences and text.'
        isCode, currCode, currText = False, [], []
        for ch in self.data:
            if ch == '\x1b':
                isCode = True
                currCode.append(ch)
                if currText:
                    yield self._textTokenType(value=''.join(currText), offset=self.glyph_offset)
                    currText = []

            elif isCode:
                currCode.append(ch)
                if ch.isalpha():
                    isCode = False
                    yield from self.create_tokens(currCode)
                    currCode = []
            else:
                if DEBUG:
                    self.counts[(ch, hex(ord(ch)))] += 1
                if ch == '\n':
                    if currText:
                        yield self._textTokenType(value=''.join(currText), offset=self.glyph_offset)
                        currText = []
                    yield NewLineToken(value=ch)
                elif ord(ch) in C0_TOKEN_NAMES:
                    if currText:
                        yield self._textTokenType(value=''.join(currText), offset=self.glyph_offset)
                        currText = []
                    yield C0Token(value=ch, offset=self.glyph_offset)
                else:
                    currText.append(ch)
        if currText:
            yield self._textTokenType(value=''.join(currText), offset=self.glyph_offset)

@dataclass
class Renderer:
    fpath:       str
    tokeniser:   Tokeniser = field(repr=False)
    _currLine:   list[ANSIToken] = field(default_factory=list, repr=False)
    _currLength: int = field(default=0, repr=False)
    _currFG:     ColorFGToken | None = field(default=None, repr=False)
    _currBG:     ColorBGToken | None = field(default=None, repr=False)
    _currSGR:    ANSIToken | None = field(default=None, repr=False)
    width:       int              = field(init=False)

    def __post_init__(self):
        self.width = self.tokeniser.width

    def split_text_token(self, s: str, remainder: int) -> Iterator[TextToken]:
        for chunk in [s[:remainder]] + list(map(''.join, batched(s[remainder:], self.width))):
            yield TextToken(value=chunk)

    def _add_current_colors(self):
        'Re-add current FG/BG colors to the current line.'
        if self._currSGR: self._currLine.append(self._currSGR)
        if self._currFG:  self._currLine.append(self._currFG)
        if self._currBG:  self._currLine.append(self._currBG)

    def gen_lines(self) -> Iterator[list[ANSIToken]]:
        'Split tokens into lines at width, or each newline char'

        newLine = [NewLineToken(value='\n')]

        for t in self.tokeniser.tokenise():
            if isinstance(t, ControlToken) and t.subtype in ('H', 's'):
                newLine = []

            if isinstance(t, Color8Token):

                tokens = list(t.generate_tokens(self._currFG, self._currBG))
                self._currLine.extend(tokens)

                for tok in tokens:
                    if isinstance(tok, SGRToken):
                        if tok.value_name == 'Reset':
                            self._currFG, self._currBG, self._currSGR = None, None, None
                        else:
                            self._currSGR = tok
                    elif isinstance(tok, Color8FGToken):
                        self._currFG = tok
                    elif isinstance(tok, Color8BGToken):
                        self._currBG = tok

            elif isinstance(t, TrueColorFGToken):
                self._currLine.append(t)
                self._currFG = t

            elif isinstance(t, TrueColorBGToken):
                self._currLine.append(t)
                self._currBG = t

            elif isinstance(t, (TextToken, CP437Token, ControlToken)):
                if self._currLength + len(str(t)) == self.width:
                    yield self._currLine + [t, SGRToken(value='0')] + newLine
                    self._currLine, self._currLength = [], 0
                    self._add_current_colors()
                    continue

                if self._currLength + len(str(t)) < self.width:
                    self._currLine.append(t)
                    self._currLength += len(str(t))
                    continue

                for chunk in self.split_text_token(str(t), self.width - self._currLength):
                    self._currLine.append(chunk)
                    self._currLength += len(str(chunk))

                    if self._currLength == self.width:
                        yield self._currLine + [SGRToken(value='0')] + newLine

                        self._currLine, self._currLength = [], 0
                        self._add_current_colors()

                    elif self._currLength > self.width:
                        raise ValueError(f'Logic error in line splitting, {self._currLength} > {self.width}')

            elif isinstance(t, NewLineToken):
                yield self._currLine + [SGRToken(value='0')] + newLine
                self._currLine, self._currLength = [], 0
                self._add_current_colors()

            else:
                self._currLine.append(t)
                if isinstance(t, SGRToken):
                    if t.value_name == 'Reset':
                        self._currFG, self._currBG, self._currSGR = None, None, None
                    else:
                        self._currSGR = t
        if self._currLine:
            yield self._currLine + [SGRToken(value='0'), EOFToken(value='')]

    def iter_lines(self) -> Iterator[str]:
        for i, line in enumerate(self.gen_lines()):
            if DEBUG:
                print(f'\n\x1b[30;103m[{i}]:\x1b[0m\n{"\n".join([el.repr() for el in line])}')
            yield ''.join(map(str, line))

    def render(self) -> str:
        'Render tokens into a string with proper line wrapping.'
        return ''.join(list(self.iter_lines()))

def parse_args() -> dict:
    parser = ArgumentParser()
    parser.add_argument('--fpath',      '-f', type=str, required=True,            help='Path to the ANSI file to render.')
    parser.add_argument('--encoding',   '-e', type=str,                           help='Specify the file encoding (cp437, iso-8859-1, ascii, utf-8) if the auto-detection was incorrect.')
    parser.add_argument('--sauce-only', '-s', action='store_true', default=False, help='Only output the SAUCE record information as JSON and exit.')
    parser.add_argument('--verbose',    '-v', action='store_true', default=False, help='Enable verbose debug output.')
    parser.add_argument('--ice-colours',      action='store_true', default=False, help='Force enabling ICE colours (non-blinking background).')
    parser.add_argument('--font-name',        type=str,                           help='Specify the font name to determine glyph offset (overrides SAUCE font).')
    parser.add_argument('--width',      '-w', type=int,                           help='Specify the output width (overrides SAUCE tinfo1).')
    return parser.parse_args().__dict__

def main():
    args = parse_args()
    global DEBUG
    DEBUG = args.pop('verbose')
    pp.enabled = not DEBUG

    # Read file once
    with open(args['fpath'], 'rb') as f:
        file_data = f.read()

    if args.get('encoding'):
        encoding = SupportedEncoding.from_value(args['encoding'])
    else:
        encoding = detect_encoding(file_data)
        dprint(f'Detected encoding: {encoding}')

    sauce_only = args.pop('sauce_only')
    sauce_record, data = SauceRecord.parse_record(file_data, encoding.value)
    sauce_extended, data = SauceRecordExtended.parse(sauce_record, data, args['fpath'], encoding)

    if sauce_only:
        pp.enabled = True
        pp.ppd(sauce_extended.asdict(), indent=2)
        return

    t = Tokeniser(**(args | {'encoding': encoding, 'sauce': sauce_extended, 'data': data}))
    r = Renderer(fpath=args['fpath'], tokeniser=t)
    dprint('\nRendered string:')
    try:
        print(r.render(), end='')
    except BrokenPipeError as e:
        dprint(f'BrokenPipeError: {e}')
        sys.exit(1)

    if DEBUG:
        dprint(pprint.pformat(t.counts.most_common()))


if __name__ == '__main__':
    main()
