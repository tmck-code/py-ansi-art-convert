#!/usr/bin/env python3

from __future__ import annotations

import pprint
import sys
from argparse import ArgumentParser
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from itertools import batched, chain, pairwise
from typing import Any, ClassVar, Iterator, List, Protocol

from laser_prynter import pp

from ansi_art_convert.encoding import SupportedEncoding, detect_encoding
from ansi_art_convert.font_data import FONT_ALIASES, FONT_OFFSETS, UNICODE_TO_CP437
from ansi_art_convert.log import DEBUG, dprint
from ansi_art_convert.sauce import SauceRecord, SauceRecordExtended
from ansi_art_convert.terminals.alacritty import AlacrittyClient


class Token(Protocol):
    def repr(self) -> str: ...
    def __str__(self) -> str: ...


@dataclass
class ANSIToken(Token):
    value: str
    value_name: str = field(init=False)
    original_value: str = field(init=False)
    value_map: ClassVar[dict[str, str]] = field(repr=False, default={})

    def __post_init__(self) -> None:
        self.original_value = self.value
        self.value_name = self.value_map.get(self.value, '')

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[37m{self.__class__.__name__:<20}\x1b[0m'
            + '  {title:<s} {value!r:<4}'.format(title='value:', value=self.value)
            + '  {title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
        ])

    def __str__(self) -> str:
        return self.value


def get_glyph_offset(font_name: str) -> int:
    if font_name in FONT_OFFSETS:
        offset = FONT_OFFSETS[font_name]
        dprint(f'font_name: {font_name!r} -> offset: {hex(offset)}')
        return offset
    else:
        raise ValueError(f'Unknown font_name: {font_name!r}')


def set_glyph_offset(offset: int) -> None:
    # update the offset class variable for both TextToken and CP437Token
    TextToken.set_offset(offset)
    CP437Token.set_offset(offset)


@dataclass
class TextToken(ANSIToken):
    offset: int = field(repr=False, default=-1)
    _offset: ClassVar[int] = 0xE100

    def __post_init__(self) -> None:
        super().__post_init__()
        # if offset wasn't supplied in constructor, use the class variable
        if self.offset == -1:
            self.offset = self._offset
        self.value = TextToken._translate_chars(self.value, self.offset)

    @staticmethod
    def _translate_chars(s: str, offset: int) -> str:
        new_values = []
        for v in s:
            if ord(v) <= 255:  # and not (0x21 <= ord(v) <= 0x7e):
                new_values.append(chr(ord(v) + offset))
            else:
                new_values.append(v)
        return ''.join(new_values)

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[32m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<17s} {value!r}'.format(title='original:', value=self.original_value),
            '  {title:<17s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<17s} {value!r}'.format(title='len:', value=len(self.value)),
        ])

    @classmethod
    def set_offset(cls, offset: int) -> None:
        'update the offset class variable for the TextToken class'

        TextToken._offset = offset


C0_TOKEN_NAMES = {
    chr(0x00): 'NUL',
    chr(0x01): 'SOH',
    chr(0x02): 'STX',
    chr(0x03): 'ETX',
    chr(0x04): 'EOT',
    chr(0x05): 'ENQ',
    chr(0x06): 'ACK',
    chr(0x07): 'BEL',
    chr(0x08): 'BS',
    chr(0x09): 'HT',
    chr(0x0A): 'LF',
    chr(0x0B): 'VT',
    chr(0x0C): 'FF',
    chr(0x0D): 'CR',
    chr(0x0E): 'SO',
    chr(0x0F): 'SI',
    chr(0x10): 'DLE',
    chr(0x11): 'DC1',
    chr(0x12): 'DC2',
    chr(0x13): 'DC3',
    chr(0x14): 'DC4',
    chr(0x15): 'NAK',
    chr(0x16): 'SYN',
    chr(0x17): 'ETB',
    chr(0x18): 'CAN',
    chr(0x19): 'EM',
    chr(0x1A): 'SUB',
    chr(0x1B): 'ESC',
    chr(0x1C): 'FS',
    chr(0x1D): 'GS',
    chr(0x1E): 'RS',
    chr(0x1F): 'US',
}


@dataclass
class C0Token(TextToken):
    value_map = C0_TOKEN_NAMES

    def __post_init__(self) -> None:
        super().__post_init__()
        self.value_name = self.value_map.get(self.original_value, '')
        if self.value_name == 'CR':
            self.value = ''

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[33m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r:<6}'.format(title='value:', value=self.value)
            + '{title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
            + '{title:<10s} {value!r:<6}'.format(title='original:', value=self.original_value)
            + '{title:<4s} {value!r}'.format(title='len:', value=len(self.value))
        ])


@dataclass
class CP437Token(ANSIToken):
    _offset: ClassVar[int] = 0xE100
    offset: int = field(repr=False, default=-1)

    def _translate_char(self, ch: str) -> str:
        n = UNICODE_TO_CP437.get(ord(ch), ord(ch))
        if n <= 255:
            return chr(n + self.offset)
        else:
            return ch

    def __post_init__(self) -> None:
        super().__post_init__()
        # if offset wasn't supplied in constructor, use the class variable
        if self.offset == -1:
            self.offset = self._offset
        self.value = ''.join([self._translate_char(v) for v in self.original_value])

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[32m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<17s} {value!r}'.format(title='original:', value=self.original_value),
            '  {title:<17s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<17s} {value!r}'.format(title='len:', value=len(self.value)),
        ])

    @classmethod
    def set_offset(cls, offset: int) -> None:
        'update the offset class variable for the CP437Token class'

        CP437Token._offset = offset


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
    subtype: str = field(init=False)
    value_map = ANSI_CONTROL_CODES

    def __post_init__(self) -> None:
        self.original_value = self.value
        self.subtype = self.value[-1]
        self.value_name = self.value_map.get(self.subtype, '')
        self.value = self.value[2:]

    def repr(self) -> str:
        lines = (
            f'\x1b[35m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r:<6}'.format(title='value:', value=self.value)
            + '{title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
            + '{title:<10s} {value!r}'.format(title='subtype:', value=self.subtype)
            + '{title:<10s} {value!r}'.format(title='original:', value=self.original_value)
            # + ' {title:<20s} {value!r}'.format(title='spaces:', value=' '*int(self.value[:-1]))
        )
        return lines

    def __str__(self) -> str:
        if self.subtype == 'C':
            return ' ' * int(self.value[:-1] or '1')
        elif self.subtype == 'H':
            return '\n'
        else:
            return ''


class ColourType(Enum):
    FG = 'fg'
    BG = 'bg'


@dataclass
class ColorFGToken(ANSIToken): ...


@dataclass
class ColorBGToken(ANSIToken): ...


@dataclass
class TrueColorFGToken(ColorFGToken):
    colour_type: ColourType = field(repr=False, default=ColourType.FG)

    def __str__(self) -> str:
        r, g, b = self.value.split(',')
        return f'\x1b[38;2;{r};{g};{b}m'

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[94m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<20s} {value!r}'.format(title='colour_type:', value=self.colour_type.value),
        ])


@dataclass
class TrueColorBGToken(ColorBGToken):
    colour_type: ColourType = field(repr=False, default=ColourType.BG)

    def __str__(self) -> str:
        r, g, b = self.value.split(',')
        return f'\x1b[48;2;{r};{g};{b}m'

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[96m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<20s} {value!r}'.format(title='colour_type:', value=self.colour_type.value),
        ])


@dataclass
class Color256FGToken(ColorFGToken):
    colour_type: ColourType = field(repr=False, default=ColourType.FG)

    def __str__(self) -> str:
        n = self.value
        return f'\x1b[38;5;{n}m'

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[34m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<20s} {value!r}'.format(title='colour_type:', value=self.colour_type.value),
        ])


@dataclass
class Color256BGToken(ColorBGToken):
    colour_type: ColourType = field(repr=False, default=ColourType.BG)

    def __str__(self) -> str:
        n = self.value
        return f'\x1b[48;5;{n}m'

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[36m{self.__class__.__name__:<20}\x1b[0m',
            '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
            '  {title:<20s} {value!r}'.format(title='colour_type:', value=self.colour_type.value),
        ])


COLOUR_8_FG_VALUES = {
    '30': 'black',
    '31': 'red',
    '32': 'green',
    '33': 'yellow',
    '34': 'blue',
    '35': 'magenta',
    '36': 'cyan',
    '37': 'white',
}
COLOUR_8_FG_BRIGHT_VALUES = {
    '90': 'bright_black',
    '91': 'bright_red',
    '92': 'bright_green',
    '93': 'bright_yellow',
    '94': 'bright_blue',
    '95': 'bright_magenta',
    '96': 'bright_cyan',
    '97': 'bright_white',
}
COLOUR_8_BG_VALUES = {
    '40': 'black',
    '41': 'red',
    '42': 'green',
    '43': 'yellow',
    '44': 'blue',
    '45': 'magenta',
    '46': 'cyan',
    '47': 'white',
}
COLOUR_8_BG_BRIGHT_VALUES = {
    '100': 'bright_black',
    '101': 'bright_red',
    '102': 'bright_green',
    '103': 'bright_yellow',
    '104': 'bright_blue',
    '105': 'bright_magenta',
    '106': 'bright_cyan',
    '107': 'bright_white',
}
COLOUR_8_FG_VALUES = COLOUR_8_FG_VALUES | COLOUR_8_FG_BRIGHT_VALUES
COLOUR_8_BG_VALUES = COLOUR_8_BG_VALUES | COLOUR_8_BG_BRIGHT_VALUES
COLOUR_8_VALUES = COLOUR_8_FG_VALUES | COLOUR_8_BG_VALUES


@dataclass
class Color8Token(ANSIToken):
    params: list[str] = field(default_factory=list)
    ice_colours: bool = field(repr=False, default=False)
    bright_bg: bool = field(init=False, default=False)
    bright_fg: bool = field(init=False, default=False)
    sgr_tokens: list[SGRToken] = field(init=False, default_factory=list)
    fg_token: Color8FGToken | None = field(init=False, default=None)
    bg_token: Color8BGToken | None = field(init=False, default=None)
    tokens: list[ANSIToken] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
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

    def __str__(self) -> str:
        return f'\x1b[{self.value}m'

    def repr(self) -> str:
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
    value_map = COLOUR_8_FG_VALUES
    colour_type: ColourType = field(repr=False, default=ColourType.FG)
    bright: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.bright:
            base_value = int(self.value)
            if base_value < 90:
                self.value = str(base_value + 60)

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[96m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r:<6}'.format(title='value:', value=self.value)
            + '{title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
            + '{title:<10s} {value!r:<6}'.format(title='original:', value=self.original_value)
        ])

    def __str__(self) -> str:
        return f'\x1b[{self.value}m'


@dataclass
class Color8BGToken(ColorBGToken):
    value_map = COLOUR_8_BG_VALUES
    colour_type: ColourType = field(repr=False, default=ColourType.BG)
    ice_colours: bool = field(default=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.original_value = self.value
        if self.ice_colours:
            self.value = str(int(self.value) + 60)

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[94m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r:<6}'.format(title='value:', value=self.value)
            + '{title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
            + '{title:<10s} {value!r:<6}'.format(title='original:', value=self.original_value)
            + '{title:<12s} {value!r}'.format(title='ice_colours:', value=self.ice_colours)
        ])

    def __str__(self) -> str:
        return f'\x1b[{self.value}m'


SGR_CODES = {
    '0': 'Reset',
    '1': 'Bold',
    '2': 'Dim',
    '3': 'Italic',
    '4': 'Underline',
    '5': 'BlinkSlow',
    '6': 'BlinkRapid',
    '7': 'ReverseVideo',
    '8': 'Conceal',
    '9': 'CrossedOut',
}


@dataclass
class SGRToken(ANSIToken):
    value_map = SGR_CODES

    def __str__(self) -> str:
        return f'\x1b[{self.value}m'

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[95m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r:<6}'.format(title='value:', value=self.value)
            + '{title:<10s} {value!r:<8}'.format(title='value_name:', value=self.value_name)
        ])


@dataclass
class NewLineToken(ANSIToken):
    def __str__(self) -> str:
        return '\n'

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[93m{self.__class__.__name__:<20}\x1b[0m'
            + '{title:<s} {value!r}'.format(title='value:', value=self.value),
        ])


@dataclass
class EOFToken(ANSIToken):
    def __str__(self) -> str:
        return ''

    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[90m{self.__class__.__name__:<20}\x1b[0m'
            + '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
        ])


@dataclass
class UnknownToken(ANSIToken):
    def repr(self) -> str:
        return '\n'.join([
            f'\x1b[91m{self.__class__.__name__:<20}\x1b[0m'
            + '  {title:<20s} {value!r}'.format(title='value:', value=self.value),
        ])


@dataclass
class EndOfFile(ANSIToken):
    value: str = ''


@dataclass
class Tokeniser:
    fpath: str
    sauce: SauceRecordExtended
    data: str
    font_name: str = field(default='', repr=False)
    encoding: SupportedEncoding = SupportedEncoding.CP437
    tokens: list[ANSIToken] = field(default_factory=list, init=False)
    glyph_offset: int = field(default=0)
    ice_colours: bool = field(default=False)
    width: int = field(default=0)
    counts: Counter[tuple[str, str]] = field(default_factory=Counter, init=False)
    _textTokenType: type = field(init=False, repr=False, default=TextToken)

    def __post_init__(self) -> None:
        if self.font_name:
            self.glyph_offset = get_glyph_offset(self.font_name)
        elif 'name' in self.sauce.font:
            self.glyph_offset = get_glyph_offset(self.sauce.font['name'])
            self.font_name = self.sauce.font['name']
        else:
            if self.encoding == SupportedEncoding.CP437:
                self.glyph_offset = get_glyph_offset('IBM VGA')

        set_glyph_offset(self.glyph_offset)

        if not self.width:
            self.width = int(self.sauce.sauce.tinfo1) or 80

        if not self.ice_colours:
            self.ice_colours = self.sauce.non_blink_mode

        if self.encoding == SupportedEncoding.CP437:
            self._textTokenType = CP437Token
        else:
            self._textTokenType = TextToken

        dprint(f'Using extended sauce: {self.sauce!r}')
        dprint(f'Width: {self.width}, Glyph offset: {hex(self.glyph_offset)}, Ice colours: {self.ice_colours}')

    def __setattr__(self, name: str, value: Any) -> None:
        if name == 'glyph_offset':
            set_glyph_offset(value)
        super().__setattr__(name, value)

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
            t = ControlToken(value=''.join(code_chars))
            return [t]

        return [UnknownToken(value=''.join(code_chars))]

    def tokenise(self) -> Iterator[ANSIToken]:
        '''
        Tokenise ANSI escape sequences and text.
        This produces a faithful representation of the tokens in the original data
        - all newlines are present
        - colour tokens are split up into their components (e.g. Color8Token -> SGRToken + Color8FGToken/Color8BGToken)
        - tokens are not merged across newlines, so the original token boundaries are preserved
        - control characters are preserved as separate tokens
        - consecutive text chars (non-newline) are merged into a single TextToken
            - any ANSI code or C0 char will cause the current TextToken to be yielded
            - then the ANSI code or C0 char will be yielded as its own token
            - then, the next TextToken will start accumulating chars
        '''

        isCode, currCode = False, []
        currText: list[str] = []
        for ch in self.data:
            if ch == '\x1b':
                isCode = True
                currCode.append(ch)
                if currText:
                    yield self._textTokenType(value=''.join(currText))
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
                        yield self._textTokenType(value=''.join(currText))
                        currText = []
                    yield NewLineToken(value=ch)
                elif ch in C0_TOKEN_NAMES:
                    if currText:
                        yield self._textTokenType(value=''.join(currText))
                        currText = []
                    yield C0Token(value=ch)
                else:
                    currText.append(ch)
        if currText:
            yield self._textTokenType(value=''.join(currText))


@dataclass
class Renderer:
    fpath: str
    tokeniser: Tokeniser = field(repr=False)
    _currLine: List[ANSIToken] = field(default_factory=list, repr=False)
    _currLength: int = field(default=0, repr=False)
    _currFG: ColorFGToken | None = field(default=None, repr=False)
    _currBG: ColorBGToken | None = field(default=None, repr=False)
    _currSGR: ANSIToken | None = field(default=None, repr=False)
    width: int = field(init=False)

    def __post_init__(self) -> None:
        self.width = self.tokeniser.width

    def split_text_token(self, t: TextToken | CP437Token, remainder: int) -> Iterator[ANSIToken]:
        s = str(t)
        for chunk in [s[:remainder]] + list(map(''.join, batched(s[remainder:], self.width))):
            yield t.__class__(value=chunk)

    def _add_current_colors(self) -> None:
        'Re-add current FG/BG colors to the current line.'
        if self._currSGR:
            self._currLine.append(self._currSGR)
        if self._currFG:
            self._currLine.append(self._currFG)
        if self._currBG:
            self._currLine.append(self._currBG)

    def gen_lines(self) -> Iterator[list[ANSIToken]]:
        'Split tokens into lines at width, or each newline char'

        skips = 0

        for t, tNext in pairwise(chain(self.tokeniser.tokenise(), [EndOfFile()])):
            if skips > 0:
                skips -= 1
                continue

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

            elif isinstance(t, ControlToken) and t.subtype == 'A':
                if isinstance(tNext, C0Token) and tNext.value_name == 'CR':
                    skips = 2
                elif isinstance(tNext, ControlToken) and tNext.value_name == 'CursorForward':
                    skips = 1

            elif isinstance(t, (TextToken, CP437Token, ControlToken)):
                dprint(f'Text/Control token: {t!r}, current line length: {self._currLength}, width: {self.width}')
                if self._currLength + len(str(t)) == self.width:
                    dprint(f'Exact fit for token: {t!r}, yielding line with reset and newline')

                    yield self._currLine + [t]

                    self._currLine, self._currLength = [], 0
                    self._add_current_colors()
                    continue

                if self._currLength + len(str(t)) < self.width:
                    dprint(
                        f'Adding token to current line: {t!r}, new line length would be: {self._currLength + len(str(t))}'
                    )
                    self._currLine.append(t)
                    self._currLength += len(str(t))
                    continue

                if not isinstance(t, (TextToken, CP437Token)):
                    continue
                for chunk in self.split_text_token(t, self.width - self._currLength):
                    self._currLine.append(chunk)
                    self._currLength += len(str(chunk))

                    if self._currLength == self.width:
                        yield self._currLine

                        self._currLine, self._currLength = [], 0
                        self._add_current_colors()

                    elif self._currLength > self.width:
                        raise ValueError(f'Logic error in line splitting, {self._currLength} > {self.width}')

            elif isinstance(t, C0Token):
                dprint(f'C0 Newline token: {t!r}, current line length: {self._currLength}, width: {self.width}')
                if t.value_name == 'CR':
                    continue

            elif isinstance(t, NewLineToken):
                dprint(f'NewLineToken: current line length: {self._currLength}, width: {self.width}')
                if (isinstance(tNext, ControlToken) and tNext.value_name == 'CursorUp') and len(
                    self._currLine
                ) < self.width:
                    continue
                yield self._currLine
                self._currLine, self._currLength = [], 0
                self._add_current_colors()
            else:
                dprint(f'Other token: {t!r}')
                self._currLine.append(t)
                if isinstance(t, SGRToken):
                    if t.value_name == 'Reset':
                        self._currFG, self._currBG, self._currSGR = None, None, None
                    else:
                        self._currSGR = t
        if self._currLine:
            yield self._currLine

    def grid(self) -> list[list[ANSIToken]]:
        'Generate a grid of tokens representing the final output, with line breaks and resets.'
        return list(self.gen_lines())

    def arrange_grid(self, grid: list[list[ANSIToken]]) -> Iterator[list[ANSIToken]]:
        '''
        Process save/restore cursor operations in the grid.
        This collapses lines that use save/restore cursor to the same line.
        Uses x/y coordinates to track cursor position for save/restore operations.
        '''
        if not grid:
            return

        output_grid: dict[int, dict[int, ANSIToken]] = {}
        x, y = 0, 0
        saved_x, saved_y = 0, 0

        line_idx = 0
        while True:
            if line_idx >= len(grid):
                break
            line, token_idx = grid[line_idx], 0

            while True:
                if token_idx >= len(line):
                    break
                token = line[token_idx]

                if isinstance(token, ControlToken):
                    if token.value_name == 'SaveCursorPosition':
                        saved_x, saved_y = x, y
                        token_idx += 1
                        continue
                    elif token.value_name == 'RestoreCursorPosition':
                        x, y = saved_x, saved_y
                        token_idx += 1
                        continue

                # Place token at current position
                if y not in output_grid:
                    output_grid[y] = {}
                output_grid[y][x] = token
                x += 1
                token_idx += 1

            # After processing line, reset x and move to next y
            line_idx += 1
            x = 0
            y += 1

        # Convert dict grid to list of lists
        for row_idx in sorted(output_grid.keys()):
            row = output_grid[row_idx]
            line_tokens = [row[col_idx] for col_idx in sorted(row.keys())]
            if line_tokens:
                yield line_tokens

    def render(self) -> str:
        '''
        Render an arranged grid of tokens to a string.
        Each line gets a reset sequence at the end.
        '''
        grid: list[list[ANSIToken]] = list(self.arrange_grid(self.grid()))
        lines = []
        for line in grid:
            lines.append(''.join(map(str, line)) + '\x1b[0m\n')
        return ''.join(lines)

    def iter_lines(self) -> Iterator[str]:
        for i, line in enumerate(self.gen_lines()):
            if DEBUG:
                print(f'\n\x1b[30;103m[{i + 1}]:\x1b[0m\n{"\n".join([el.repr() for el in line])}')
            yield ''.join(map(str, line)) + '\x1b[0m\n'
        yield str(EOFToken(value=''))


def parse_args() -> dict[str, Any]:
    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('--fpath', '-f', type=str, help='Path to the ANSI file to render.')
    group.add_argument(
        '--launch-alacritty',
        action='store_true',
        default=False,
        help='Launch the rendered output in Alacritty.',
    )

    parser.add_argument(
        '--encoding',
        '-e',
        type=str,
        help='Specify the file encoding (cp437, iso-8859-1, ascii, utf-8) if the auto-detection was incorrect.',
    )
    parser.add_argument(
        '--sauce-only',
        '-s',
        action='store_true',
        default=False,
        help='Only output the SAUCE record information as JSON and exit.',
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        default=False,
        help='Enable verbose debug output.',
    )
    parser.add_argument(
        '--ice-colours',
        action='store_true',
        default=False,
        help='Force enabling ICE colours (non-blinking background).',
    )
    parser.add_argument(
        '--font-name',
        '-F',
        type=str,
        choices=FONT_ALIASES.keys(),
        help='Specify the font name to determine glyph offset (overrides SAUCE font).',
    )
    parser.add_argument(
        '--width',
        '-w',
        type=int,
        help='Specify the output width (overrides SAUCE tinfo1).',
    )

    return parser.parse_args().__dict__


def parse_info(args: dict[str, Any]) -> tuple[SupportedEncoding, SauceRecordExtended, str]:
    with open(args['fpath'], 'rb') as f:
        file_data = f.read()

    if args.get('encoding'):
        encoding = SupportedEncoding.from_value(args['encoding'])
    else:
        encoding = detect_encoding(file_data)

    sauce_record, data = SauceRecord.parse_record(file_data, encoding.value)
    sauce_extended, data = SauceRecordExtended.parse(sauce_record, data, args['fpath'], encoding)

    return encoding, sauce_extended, data


def run(args: dict[str, Any]) -> None:
    if args.get('launch_alacritty'):
        AlacrittyClient().launch()
    else:
        args.pop('launch_alacritty', None)

    if 'font_name' in args and args['font_name']:
        args['font_name'] = FONT_ALIASES[args['font_name']]
    global DEBUG
    DEBUG = args.pop('verbose', False)
    pp.enabled = not DEBUG

    sauce_only = args.pop('sauce_only', False)
    encoding, sauce_extended, data = parse_info(args)

    if sauce_only:
        pp.enabled = True
        pp.ppd(sauce_extended.asdict(), indent=2)
        return

    t = Tokeniser(**(args | {'encoding': encoding, 'sauce': sauce_extended, 'data': data}))
    r = Renderer(fpath=args['fpath'], tokeniser=t)
    dprint('\nRendered string:')
    try:
        if AlacrittyClient.session_is_custom_alacritty():
            AlacrittyClient().with_font(t.font_name).update_config()
        print(r.render(), end='')
    except BrokenPipeError as e:
        dprint(f'BrokenPipeError: {e}')
        sys.exit(1)

    if DEBUG:
        dprint(pprint.pformat(t.counts.most_common()))


def main() -> None:
    run(parse_args())


if __name__ == '__main__':
    main()
