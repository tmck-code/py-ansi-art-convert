#!/usr/bin/env python3

from __future__ import annotations
from argparse import ArgumentParser
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from itertools import chain, batched
import os
import pprint
import sys
from typing import Iterator, NamedTuple, Tuple, ClassVar

from laser_prynter import pp

from .font_data import FONT_DATA, FILE_DATA_TYPES

DEBUG = False
def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs, file=sys.stderr)

@dataclass
class ANSIToken:
    value:     str
    value_name: str = field(default='')
    value_map: dict = field(repr=False, default_factory=dict)
    original_value: str = field(init=False)

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
        if '1+' in font_name:
            offset = 0xE000
        elif '2+' in font_name:
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

# Dictionary mapping Unicode character to CP437 byte value
# Only includes mappings where Unicode codepoint != CP437 value
UNICODE_TO_CP437 = {
    0xc7: 0x80,  # LATIN CAPITAL LETTER C WITH CEDILLA
    0xfc: 0x81,  # LATIN SMALL LETTER U WITH DIAERESIS
    0xe9: 0x82,  # LATIN SMALL LETTER E WITH ACUTE
    0xe2: 0x83,  # LATIN SMALL LETTER A WITH CIRCUMFLEX
    0xe4: 0x84,  # LATIN SMALL LETTER A WITH DIAERESIS
    0xe0: 0x85,  # LATIN SMALL LETTER A WITH GRAVE
    0xe5: 0x86,  # LATIN SMALL LETTER A WITH RING ABOVE
    0xe7: 0x87,  # LATIN SMALL LETTER C WITH CEDILLA
    0xea: 0x88,  # LATIN SMALL LETTER E WITH CIRCUMFLEX
    0xeb: 0x89,  # LATIN SMALL LETTER E WITH DIAERESIS
    0xe8: 0x8a,  # LATIN SMALL LETTER E WITH GRAVE
    0xef: 0x8b,  # LATIN SMALL LETTER I WITH DIAERESIS
    0xee: 0x8c,  # LATIN SMALL LETTER I WITH CIRCUMFLEX
    0xec: 0x8d,  # LATIN SMALL LETTER I WITH GRAVE
    0xc4: 0x8e,  # LATIN CAPITAL LETTER A WITH DIAERESIS
    0xc5: 0x8f,  # LATIN CAPITAL LETTER A WITH RING ABOVE
    0xc9: 0x90,  # LATIN CAPITAL LETTER E WITH ACUTE
    0xe6: 0x91,  # LATIN SMALL LIGATURE AE
    0xc6: 0x92,  # LATIN CAPITAL LIGATURE AE
    0xf4: 0x93,  # LATIN SMALL LETTER O WITH CIRCUMFLEX
    0xf6: 0x94,  # LATIN SMALL LETTER O WITH DIAERESIS
    0xf2: 0x95,  # LATIN SMALL LETTER O WITH GRAVE
    0xfb: 0x96,  # LATIN SMALL LETTER U WITH CIRCUMFLEX
    0xf9: 0x97,  # LATIN SMALL LETTER U WITH GRAVE
    0xff: 0x98,  # LATIN SMALL LETTER Y WITH DIAERESIS
    0xd6: 0x99,  # LATIN CAPITAL LETTER O WITH DIAERESIS
    0xdc: 0x9a,  # LATIN CAPITAL LETTER U WITH DIAERESIS
    0xa2: 0x9b,  # CENT SIGN
    0xa3: 0x9c,  # POUND SIGN
    0xa5: 0x9d,  # YEN SIGN
    0x20a7: 0x9e,  # PESETA SIGN
    0x0192: 0x9f,  # LATIN SMALL LETTER F WITH HOOK
    0xe1: 0xa0,  # LATIN SMALL LETTER A WITH ACUTE
    0xed: 0xa1,  # LATIN SMALL LETTER I WITH ACUTE
    0xf3: 0xa2,  # LATIN SMALL LETTER O WITH ACUTE
    0xfa: 0xa3,  # LATIN SMALL LETTER U WITH ACUTE
    0xf1: 0xa4,  # LATIN SMALL LETTER N WITH TILDE
    0xd1: 0xa5,  # LATIN CAPITAL LETTER N WITH TILDE
    0xaa: 0xa6,  # FEMININE ORDINAL INDICATOR
    0xba: 0xa7,  # MASCULINE ORDINAL INDICATOR
    0xbf: 0xa8,  # INVERTED QUESTION MARK
    0x2310: 0xa9,  # REVERSED NOT SIGN
    0xac: 0xaa,  # NOT SIGN
    0xbd: 0xab,  # VULGAR FRACTION ONE HALF
    0xbc: 0xac,  # VULGAR FRACTION ONE QUARTER
    0xa1: 0xad,  # INVERTED EXCLAMATION MARK
    0xab: 0xae,  # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
    0xbb: 0xaf,  # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
    0x2591: 0xb0,  # LIGHT SHADE
    0x2592: 0xb1,  # MEDIUM SHADE
    0x2593: 0xb2,  # DARK SHADE
    0x2502: 0xb3,  # BOX DRAWINGS LIGHT VERTICAL
    0x2524: 0xb4,  # BOX DRAWINGS LIGHT VERTICAL AND LEFT
    0x2561: 0xb5,  # BOX DRAWINGS VERTICAL SINGLE AND LEFT DOUBLE
    0x2562: 0xb6,  # BOX DRAWINGS VERTICAL DOUBLE AND LEFT SINGLE
    0x2556: 0xb7,  # BOX DRAWINGS DOWN DOUBLE AND LEFT SINGLE
    0x2555: 0xb8,  # BOX DRAWINGS DOWN SINGLE AND LEFT DOUBLE
    0x2563: 0xb9,  # BOX DRAWINGS DOUBLE VERTICAL AND LEFT
    0x2551: 0xba,  # BOX DRAWINGS DOUBLE VERTICAL
    0x2557: 0xbb,  # BOX DRAWINGS DOUBLE DOWN AND LEFT
    0x255d: 0xbc,  # BOX DRAWINGS DOUBLE UP AND LEFT
    0x255c: 0xbd,  # BOX DRAWINGS UP DOUBLE AND LEFT SINGLE
    0x255b: 0xbe,  # BOX DRAWINGS UP SINGLE AND LEFT DOUBLE
    0x2510: 0xbf,  # BOX DRAWINGS LIGHT DOWN AND LEFT
    0x2514: 0xc0,  # BOX DRAWINGS LIGHT UP AND RIGHT
    0x2534: 0xc1,  # BOX DRAWINGS LIGHT UP AND HORIZONTAL
    0x252c: 0xc2,  # BOX DRAWINGS LIGHT DOWN AND HORIZONTAL
    0x251c: 0xc3,  # BOX DRAWINGS LIGHT VERTICAL AND RIGHT
    0x2500: 0xc4,  # BOX DRAWINGS LIGHT HORIZONTAL
    0x253c: 0xc5,  # BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL
    0x255e: 0xc6,  # BOX DRAWINGS VERTICAL SINGLE AND RIGHT DOUBLE
    0x255f: 0xc7,  # BOX DRAWINGS VERTICAL DOUBLE AND RIGHT SINGLE
    0x255a: 0xc8,  # BOX DRAWINGS DOUBLE UP AND RIGHT
    0x2554: 0xc9,  # BOX DRAWINGS DOUBLE DOWN AND RIGHT
    0x2569: 0xca,  # BOX DRAWINGS DOUBLE UP AND HORIZONTAL
    0x2566: 0xcb,  # BOX DRAWINGS DOUBLE DOWN AND HORIZONTAL
    0x2560: 0xcc,  # BOX DRAWINGS DOUBLE VERTICAL AND RIGHT
    0x2550: 0xcd,  # BOX DRAWINGS DOUBLE HORIZONTAL
    0x256c: 0xce,  # BOX DRAWINGS DOUBLE VERTICAL AND HORIZONTAL
    0x2567: 0xcf,  # BOX DRAWINGS UP SINGLE AND HORIZONTAL DOUBLE
    0x2568: 0xd0,  # BOX DRAWINGS UP DOUBLE AND HORIZONTAL SINGLE
    0x2564: 0xd1,  # BOX DRAWINGS DOWN SINGLE AND HORIZONTAL DOUBLE
    0x2565: 0xd2,  # BOX DRAWINGS DOWN DOUBLE AND HORIZONTAL SINGLE
    0x2559: 0xd3,  # BOX DRAWINGS UP DOUBLE AND RIGHT SINGLE
    0x2558: 0xd4,  # BOX DRAWINGS UP SINGLE AND RIGHT DOUBLE
    0x2552: 0xd5,  # BOX DRAWINGS DOWN SINGLE AND RIGHT DOUBLE
    0x2553: 0xd6,  # BOX DRAWINGS DOWN DOUBLE AND RIGHT SINGLE
    0x256b: 0xd7,  # BOX DRAWINGS VERTICAL DOUBLE AND HORIZONTAL SINGLE
    0x256a: 0xd8,  # BOX DRAWINGS VERTICAL SINGLE AND HORIZONTAL DOUBLE
    0x2518: 0xd9,  # BOX DRAWINGS LIGHT UP AND LEFT
    0x250c: 0xda,  # BOX DRAWINGS LIGHT DOWN AND RIGHT
    0x2588: 0xdb,  # FULL BLOCK
    0x2584: 0xdc,  # LOWER HALF BLOCK
    0x258c: 0xdd,  # LEFT HALF BLOCK
    0x2590: 0xde,  # RIGHT HALF BLOCK
    0x2580: 0xdf,  # UPPER HALF BLOCK
    0x03b1: 0xe0,  # GREEK SMALL LETTER ALPHA
    0xdf: 0xe1,  # LATIN SMALL LETTER SHARP S
    0x0393: 0xe2,  # GREEK CAPITAL LETTER GAMMA
    0x03c0: 0xe3,  # GREEK SMALL LETTER PI
    0x03a3: 0xe4,  # GREEK CAPITAL LETTER SIGMA
    0x03c3: 0xe5,  # GREEK SMALL LETTER SIGMA
    0xb5: 0xe6,  # MICRO SIGN
    0x03c4: 0xe7,  # GREEK SMALL LETTER TAU
    0x03a6: 0xe8,  # GREEK CAPITAL LETTER PHI
    0x0398: 0xe9,  # GREEK CAPITAL LETTER THETA
    0x03a9: 0xea,  # GREEK CAPITAL LETTER OMEGA
    0x03b4: 0xeb,  # GREEK SMALL LETTER DELTA
    0x221e: 0xec,  # INFINITY
    0x03c6: 0xed,  # GREEK SMALL LETTER PHI
    0x03b5: 0xee,  # GREEK SMALL LETTER EPSILON
    0x2229: 0xef,  # INTERSECTION
    0x2261: 0xf0,  # IDENTICAL TO
    0xb1: 0xf1,  # PLUS-MINUS SIGN
    0x2265: 0xf2,  # GREATER-THAN OR EQUAL TO
    0x2264: 0xf3,  # LESS-THAN OR EQUAL TO
    0x2320: 0xf4,  # TOP HALF INTEGRAL
    0x2321: 0xf5,  # BOTTOM HALF INTEGRAL
    0xf7: 0xf6,  # DIVISION SIGN
    0x2248: 0xf7,  # ALMOST EQUAL TO
    0xb0: 0xf8,  # DEGREE SIGN
    0x2219: 0xf9,  # BULLET OPERATOR
    0xb7: 0xfa,  # MIDDLE DOT
    0x221a: 0xfb,  # SQUARE ROOT
    0x207f: 0xfc,  # SUPERSCRIPT LATIN SMALL LETTER N
    0xb2: 0xfd,  # SUPERSCRIPT TWO
    0x25a0: 0xfe,  # BLACK SQUARE
    0xa0: 0xff,  # NO-BREAK SPACE
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


@dataclass
class SauceRecordExtended:
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

    aspect_ratio_map: ClassVar[dict] = {
        (0, 0): 'Legacy value. No preference.',
        (0, 1): 'Image was created for a legacy device. When displayed on a device with square pixels, either the font or the image needs to be stretched.',
        (1, 0): 'Image was created for a modern device with square pixels. No stretching is desired on a device with square pixels.',
        (1, 1): 'Not currently a valid value.'
    }
    letter_spacing_map: ClassVar[dict] = {
        (0, 0): 'Legacy value. No preference.',
        (0, 1): 'Select 8 pixel font.',
        (1, 0): 'Select 9 pixel font.',
        (1, 1): 'Not currently a valid value.'
    }
    tinfo_names: ClassVar[list[str]] = ['tinfo1', 'tinfo2', 'tinfo3', 'tinfo4']
    font_map: ClassVar[dict] = FONT_DATA
    tinfo_map: ClassVar[dict] = FILE_DATA_TYPES

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
            'aspect_ratio':   SauceRecordExtended.aspect_ratio_map.get((ar1, ar2), 'Unknown'),
            'letter_spacing': SauceRecordExtended.letter_spacing_map.get((ls1, ls2), 'Unknown'),
            'non_blink_mode': bool(b),
        }

    @staticmethod
    def parse_font(font_name: str) -> dict:
        dprint(f'Parsing font data for font name: {font_name!r}')
        return SauceRecordExtended.font_map.get(font_name, {})

    @staticmethod
    def parse_tinfo_field(tinfo_key: str, sauce: SauceRecord) -> dict:
        if sauce.data_type == 5:
            # ('BinaryText', 'Variable'): {'tinfo1': '0', 'tinfo2': '0', 'tinfo3': '0', 'tinfo4': '0' }``
            raise NotImplementedError('SAUCE tinfo parsing for data_type 5 (BinaryText) is not implemented.')
        return {
            'name':  SauceRecordExtended.tinfo_map.get((sauce.data_type, sauce.file_type), {}).get(tinfo_key, '0'),
            'value': getattr(sauce, tinfo_key),
        }

    @staticmethod
    def parse_tinfo(sauce: SauceRecord) -> dict:
        info = {}
        for name in SauceRecordExtended.tinfo_names:
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
    def parse_record(file_path: str, encoding) -> Tuple[SauceRecord, str]:
        with open(file_path, 'rb') as f:
            file_data = f.read()

        data, sauce_data = file_data[:-128], file_data[-128:]

        if not (sauce_data and sauce_data.startswith(b'SAUCE')):
            dprint(f'No SAUCE record found: {sauce_data[:5]!r}')
            return SauceRecord(), file_data.decode(encoding)

        values = {}
        for key, (start, end) in SauceRecord.offsets().items():
            values[key] = SauceRecord.parse_field(key, sauce_data[start:end], encoding)

        return SauceRecord(*values.values()), data.decode(encoding)

class SupportedEncoding(Enum):
    CP437      = 'cp437'
    ISO_8859_1 = 'iso-8859-1'
    ASCII      = 'ascii'
    UTF_8      = 'utf-8'

    @staticmethod
    def from_value(value: str) -> SupportedEncoding:
        for encoding in SupportedEncoding:
            if encoding.value == value:
                return encoding
        raise ValueError(f'Unsupported encoding: {value}')

# blockChars = [][]byte{[]byte("░"), []byte("▒"), []byte("█"), []byte("▄"), []byte("▐"), []byte("▀")}
CP437_BLOCK_MAP = {
    0xB0: '░',
    0xB1: '▒',
    0xDB: '█',
    0xDC: '▄',
    0xDD: '▐',
    0xDF: '▀',
}
CP437_BOX_MAP = {
    0xC0: '└',
    0xD9: '┘',
    0xC3: '├',
    0xC2: '┬',
    0xC1: '┐',
    0xB4: '┤',
}
ISO_8859_1_BOX_MAP = {
    0x7c: '|',
    0x5c: '\\',
    0x2f: '/',
    0xaf: '¯',
    0x5f: '_',
}
POPULAR_CHAR_MAP = {
    'Ñ': {SupportedEncoding.CP437: 0xA5, SupportedEncoding.ISO_8859_1: 0xD1},
}
ODD_ONES_OUT = [
    {
        'points':     1,
        'points_for': SupportedEncoding.ISO_8859_1,
        'char':       {0xAF: '¯'},                       # in CP437 this char is: ['»' hex=0xaf]
        'regulars':   {0x2D: '-', 0x3A: ':', 0x7C: '|'}, # these decode identically in ISO-8859-1 and CP437
    }
]

def detect_encoding(fpath: str) -> SupportedEncoding:
    'Detect file encoding based on presence of CP437 block characters.'
    with open(fpath, 'rb') as f:
        data = f.read()
    points = Counter(list(SupportedEncoding.__members__.values()))

    for char, version in POPULAR_CHAR_MAP.items():
        for encoding, byt in version.items():
            count = data.count(byt)
            if count == 0:
                continue
            dprint(f'> [{encoding.value} +1] Detected popular character in file: {(char, encoding.value, count)}')
            points[encoding] += 1

    for odd_char in ODD_ONES_OUT:
        for byt, replacement in odd_char['char'].items():
            count = data.count(byt)
            if count == 0:
                break

        counts = []
        for byt, replacement in odd_char['regulars'].items():
            count = data.count(byt)
            if count == 0:
                continue
            counts.append((replacement, count))
        if len(counts) > 1:
            dprint(f'> [{odd_char["points_for"].value} +{odd_char["points"]}] Detected odd-one-out characters in file: {counts}')
            points[encoding] += odd_char['points']

    iso_box_counts = Counter()
    for byte in ISO_8859_1_BOX_MAP.keys():
        iso_box_counts[byte] = data.count(byte)

    counts = Counter()
    for byte in (CP437_BOX_MAP | CP437_BLOCK_MAP).keys():
        count = data.count(byte)
        if count > 0:
            counts[byte] = data.count(byte)

    if len(counts) > 1:
        if counts.total() < iso_box_counts.total():
            dprint(f'> [ISO +1] Detected more ISO-8859-1 box characters in file than CP437: {iso_box_counts.total()} vs {counts.total()}')
            points[SupportedEncoding.ISO_8859_1] += 1
        else:
            dprint(f'> [CP437 +1] Detected CP437 characters in file: {counts}')
            points[SupportedEncoding.CP437] += 1

    if DEBUG:
        pp.ppd({'points': {k.name: v for k,v in points.items()}}, indent=2)
    return points.most_common(1)[0][0]


@dataclass
class Tokeniser:
    fpath:        str
    sauce:        SauceRecordExtended
    data:         str
    encoding:     SupportedEncoding   = SupportedEncoding.CP437
    tokens:       list[ANSIToken]     = field(default_factory=list, init=False)
    glyph_offset: int                 = field(init=False, default=0xE000)
    ice_colours:  bool                = field(default=False)
    font_name:    str                 = field(default='')
    width:        int                 = field(default=0)
    counts:       Counter[tuple[str, str]] = field(default_factory=Counter, init=False)
    _textTokenType: type = field(init=False, repr=False, default=TextToken)

    def __post_init__(self):
        if self.font_name:
            self.glyph_offset = get_glyph_offset(self.font_name)
        elif 'name' in self.sauce.font:
            self.glyph_offset = get_glyph_offset(self.sauce.font['name'])

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

    if args.get('encoding'):
        encoding = SupportedEncoding.from_value(args['encoding'])
    else:
        encoding = detect_encoding(args['fpath'])
        dprint(f'Detected encoding: {encoding}')

    sauce_only = args.pop('sauce_only')
    sauce_record, data = SauceRecord.parse_record(args['fpath'], encoding.value)
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
