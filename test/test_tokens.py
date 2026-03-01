#!/usr/bin/env python3
'Unit tests for all Token classes in convert.py'

from dataclasses import asdict

from ansi_art_convert.convert import (
    ANSI_CONTROL_CODES,
    C0_TOKEN_NAMES,
    COLOUR_8_BG_VALUES,
    COLOUR_8_FG_VALUES,
    SGR_CODES,
    ANSIToken,
    C0Token,
    Color8BGToken,
    Color8FGToken,
    Color8Token,
    Color256BGToken,
    Color256FGToken,
    ColourType,
    ControlToken,
    CP437Token,
    EOFToken,
    NewLineToken,
    SGRToken,
    TextToken,
    TrueColorBGToken,
    TrueColorFGToken,
    UnknownToken,
)
from ansi_art_convert.font_data import FONT_OFFSETS


class TestANSIToken:
    'Test the base ANSIToken class'

    def test_basic_token_creation(self) -> None:
        token = ANSIToken(value='test')
        expected = {
            'value': 'test',
            'original_value': 'test',
            'value_name': '',
            'value_map': {},
        }

        assert asdict(token) == expected

    def test_token_with_value_map(self) -> None:
        token = ANSIToken(value='A', value_map={'A': 'Letter A'})
        expected = {
            'value': 'A',
            'original_value': 'A',
            'value_name': 'Letter A',
            'value_map': {'A': 'Letter A'},
        }
        assert asdict(token) == expected

    def test_token_str(self) -> None:
        result = ANSIToken(value='hello').__str__()
        expected = 'hello'
        assert result == expected


class TestTextToken:
    'Test TextToken with glyph offset conversion'

    def test_text_token_basic(self) -> None:
        offset = 0xE100
        token = TextToken(value='A', offset=offset)
        expected = {
            'hex_values': [],
            'offset': offset,
            'value': chr(ord('A') + offset),
            'original_value': 'A',
            'value_name': '',
            'value_map': {},
        }
        assert asdict(token) == expected

    def test_text_token_multiple_chars(self) -> None:
        token = TextToken(value='ABC', offset=0xE100)
        expected = {
            'hex_values': [],
            'offset': 0xE100,
            'value': ''.join(chr(ord(c) + 0xE100) for c in 'ABC'),
            'original_value': 'ABC',
            'value_name': '',
            'value_map': {},
        }
        assert asdict(token) == expected

    def test_text_token_high_unicode_preserved(self) -> None:
        # Characters > 255 should not be offset
        token = TextToken(value='♥', offset=0xE100)
        expected = {
            'hex_values': [],
            'offset': 0xE100,
            'value': '♥',
            'original_value': '♥',
            'value_name': '',
            'value_map': {},
        }
        assert asdict(token) == expected

    def test_text_token_mixed(self) -> None:
        token = TextToken(value='A♥B', offset=0xE100)
        expected = {
            'hex_values': [],
            'offset': 0xE100,
            'value': chr(ord('A') + 0xE100) + '♥' + chr(ord('B') + 0xE100),
            'original_value': 'A♥B',
            'value_name': '',
            'value_map': {},
        }
        assert asdict(token) == expected

    def test_text_token_zero_offset(self) -> None:
        token = TextToken(value='ABC', offset=0)
        expected = {
            'hex_values': [],
            'offset': 0,
            'value': 'ABC',
            'original_value': 'ABC',
            'value_name': '',
            'value_map': {},
        }
        assert asdict(token) == expected


class TestC0Token:
    'Test C0 control character tokens'

    def test_c0_token_cr(self) -> None:
        for offset in FONT_OFFSETS.values():
            token = C0Token(value='\r', offset=offset)
            expected = {
                'value': '',
                'original_value': '\r',
                'value_name': 'CR',
                'value_map': C0_TOKEN_NAMES,
                'offset': offset,
                'hex_values': [],
            }
            assert asdict(token) == expected

    def test_c0_token_lf(self) -> None:
        for offset in FONT_OFFSETS.values():
            token = C0Token(value='\n', offset=offset)
            assert token.value_name == 'LF'
            assert len(token.value) > 0

    def test_c0_token_tab(self) -> None:
        for offset in FONT_OFFSETS.values():
            token = C0Token(value='\t', offset=offset)
        assert token.value_name == 'HT'

    def test_c0_token_bell(self) -> None:
        for offset in FONT_OFFSETS.values():
            token = C0Token(value='\x07', offset=offset)
            assert token.value_name == 'BEL'

    def test_c0_token_backspace(self) -> None:
        for offset in FONT_OFFSETS.values():
            token = C0Token(value='\x08', offset=offset)
            assert token.value_name == 'BS'


class TestCP437Token:
    'Test CP437 encoding token'

    def test_cp437_basic_ascii(self) -> None:
        token = CP437Token(value='A', offset=0xE100)
        assert ord(token.value[0]) == ord('A') + 0xE100

    def test_cp437_special_char(self) -> None:
        token = CP437Token(value='☺', offset=0xE100)
        expected = {
            'value': '☺',  # '☺' is CP437 code 1
            'original_value': '☺',
            'value_name': '',
            'value_map': {},
            'offset': 0xE100,
            'hex_values': [],
        }
        assert asdict(token) == expected

    def test_cp437_multiple_chars(self) -> None:
        token = CP437Token(value='ABC', offset=0xE100)
        expected = ''.join(chr(0xE100 + ord(c)) for c in 'ABC')
        assert token.value == expected


class TestControlToken:
    'Test ANSI control sequence tokens'


class TestControlTokenCursorUp:
    def test_cursor_up(self) -> None:
        token = ControlToken(value='\x1b[A')
        expected = {
            'value': 'A',
            'original_value': '\x1b[A',
            'value_name': 'CursorUp',
            'value_map': ANSI_CONTROL_CODES,
            'subtype': 'A',
        }
        assert asdict(token) == expected


class TestControlTokenCursorDown:
    def test_cursor_down(self) -> None:
        token = ControlToken(value='\x1b[5B')
        expected = {
            'value': '5B',
            'original_value': '\x1b[5B',
            'value_name': 'CursorDown',
            'value_map': ANSI_CONTROL_CODES,
            'subtype': 'B',
        }
        assert asdict(token) == expected

    def test_cursor_forward_1_space_default(self) -> None:
        token = ControlToken(value='\x1b[C')
        expected = {
            'value': 'C',
            'original_value': '\x1b[C',
            'value_name': 'CursorForward',
            'value_map': ANSI_CONTROL_CODES,
            'subtype': 'C',
        }
        assert asdict(token) == expected
        assert str(token) == ' '

    def test_cursor_forward_1_space(self) -> None:
        token = ControlToken(value='\x1b[1C')
        expected = {
            'value': '1C',
            'original_value': '\x1b[1C',
            'value_name': 'CursorForward',
            'value_map': ANSI_CONTROL_CODES,
            'subtype': 'C',
        }
        assert asdict(token) == expected
        assert str(token) == ' ' * 1

    def test_cursor_forward_10_spaces(self) -> None:
        token = ControlToken(value='\x1b[10C')
        expected = {
            'value': '10C',
            'original_value': '\x1b[10C',
            'value_name': 'CursorForward',
            'value_map': ANSI_CONTROL_CODES,
            'subtype': 'C',
        }
        assert asdict(token) == expected
        assert str(token) == ' ' * 10

    def test_cursor_forward_1000_spaces(self) -> None:
        token = ControlToken(value='\x1b[1000C')
        expected = {
            'value': '1000C',
            'original_value': '\x1b[1000C',
            'value_name': 'CursorForward',
            'value_map': ANSI_CONTROL_CODES,
            'subtype': 'C',
        }
        assert asdict(token) == expected
        assert str(token) == ' ' * 1000


class TestControlTokenCursorPosition:
    def test_cursor_position(self) -> None:
        token = ControlToken(value='\x1b[10;20H')
        expected = {
            'value': '10;20H',
            'original_value': '\x1b[10;20H',
            'value_name': 'CursorPosition',
            'value_map': ANSI_CONTROL_CODES,
            'subtype': 'H',
        }
        assert asdict(token) == expected
        assert str(token) == '\n'


class TestControlTokenEraseInLine:
    def test_erase_in_line(self) -> None:
        token = ControlToken(value='\x1b[K')
        expected = {
            'value': 'K',
            'original_value': '\x1b[K',
            'value_name': 'EraseInLine',
            'value_map': ANSI_CONTROL_CODES,
            'subtype': 'K',
        }
        assert asdict(token) == expected


class TestTrueColorTokens:
    'Test 24-bit true color tokens'

    def test_true_color_fg(self) -> None:
        token = TrueColorFGToken(value='255,128,64')
        expected = {
            'value': '255,128,64',
            'original_value': '255,128,64',
            'value_name': '',
            'value_map': {},
            'colour_type': ColourType.FG,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[38;2;255;128;64m'

    def test_true_color_bg(self) -> None:
        token = TrueColorBGToken(value='0,128,255')
        expected = {
            'value': '0,128,255',
            'original_value': '0,128,255',
            'value_name': '',
            'value_map': {},
            'colour_type': ColourType.BG,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[48;2;0;128;255m'

    def test_true_color_fg_black(self) -> None:
        token = TrueColorFGToken(value='0,0,0')
        assert str(token) == '\x1b[38;2;0;0;0m'

    def test_true_color_bg_white(self) -> None:
        token = TrueColorBGToken(value='255,255,255')
        assert str(token) == '\x1b[48;2;255;255;255m'


class TestColor256Tokens:
    'Test 256-color palette tokens'

    def test_color256_fg(self) -> None:
        token = Color256FGToken(value='42')
        expected = {
            'value': '42',
            'original_value': '42',
            'value_name': '',
            'value_map': {},
            'colour_type': ColourType.FG,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[38;5;42m'

    def test_color256_bg(self) -> None:
        token = Color256BGToken(value='196')
        expected = {
            'value': '196',
            'original_value': '196',
            'value_name': '',
            'value_map': {},
            'colour_type': ColourType.BG,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[48;5;196m'

    def test_color256_fg_zero(self) -> None:
        token = Color256FGToken(value='0')
        assert str(token) == '\x1b[38;5;0m'

    def test_color256_bg_max(self) -> None:
        token = Color256BGToken(value='255')
        assert str(token) == '\x1b[48;5;255m'


class TestColor8FGToken:
    'Test 8-color foreground tokens'

    def test_color8_fg_red(self) -> None:
        token = Color8FGToken(value='31')
        expected = {
            'value': '31',
            'original_value': '31',
            'value_name': 'red',
            'value_map': COLOUR_8_FG_VALUES,
            'colour_type': ColourType.FG,
            'bright': False,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[31m'

    def test_color8_fg_blue(self) -> None:
        token = Color8FGToken(value='34')
        expected = {
            'value': '34',
            'original_value': '34',
            'value_name': 'blue',
            'value_map': COLOUR_8_FG_VALUES,
            'colour_type': ColourType.FG,
            'bright': False,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[34m'

    def test_color8_fg_bright_red(self) -> None:
        token = Color8FGToken(value='91')
        expected = {
            'value': '91',
            'original_value': '91',
            'value_name': 'bright_red',
            'value_map': COLOUR_8_FG_VALUES,
            'colour_type': ColourType.FG,
            'bright': False,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[91m'

    def test_color8_fg_with_bright_flag(self) -> None:
        # When bright=True, base colors should be converted to bright
        token = Color8FGToken(value='31', bright=True)
        expected = {
            'value': '91',  # 31 + 60 = 91
            'original_value': '31',
            'value_name': 'red',  # value_name is set before transformation
            'value_map': COLOUR_8_FG_VALUES,
            'colour_type': ColourType.FG,
            'bright': True,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[91m'

    def test_color8_fg_bright_with_bright_flag(self) -> None:
        # Already bright colors should not change
        token = Color8FGToken(value='91', bright=True)
        assert token.value == '91'


class TestColor8BGToken:
    'Test 8-color background tokens'

    def test_color8_bg_red(self) -> None:
        token = Color8BGToken(value='41')
        assert token.colour_type == ColourType.BG
        expected = {
            'value': '41',
            'original_value': '41',
            'value_name': 'red',
            'value_map': COLOUR_8_BG_VALUES,
            'colour_type': ColourType.BG,
            'ice_colours': False,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[41m'

    def test_color8_bg_blue(self) -> None:
        token = Color8BGToken(value='44')
        expected = {
            'value': '44',
            'original_value': '44',
            'value_name': 'blue',
            'value_map': COLOUR_8_BG_VALUES,
            'colour_type': ColourType.BG,
            'ice_colours': False,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[44m'

    def test_color8_bg_ice_colours(self) -> None:
        # With ice_colours=True, background colors get +60
        token = Color8BGToken(value='41', ice_colours=True)
        expected = {
            'value': '101',  # 41 + 60 = 101
            'original_value': '41',
            'value_name': 'red',  # value_name is set before transformation
            'value_map': COLOUR_8_BG_VALUES,
            'colour_type': ColourType.BG,
            'ice_colours': True,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[101m'

    def test_color8_bg_bright_ice_colours(self) -> None:
        token = Color8BGToken(value='101', ice_colours=True)
        assert token.value == '161'  # 101 + 60 = 161


class TestColor8Token:
    'Test composite 8-color token that generates sub-tokens'

    def test_color8_token_fg_only(self) -> None:
        token = Color8Token(value='31', params=['31'])
        expected_fg = {
            'bright': False,
            'colour_type': ColourType.FG,
            'original_value': '31',
            'value': '31',
            'value_map': COLOUR_8_FG_VALUES,
            'value_name': 'red',
        }
        expected = {
            'bg_token': None,
            'bright_bg': False,
            'bright_fg': False,
            'fg_token': expected_fg,
            'ice_colours': False,
            'original_value': '31',
            'params': ['31'],
            'sgr_tokens': [],
            'tokens': [expected_fg],
            'value': '31',
            'value_map': {},
            'value_name': '',
        }
        assert asdict(token) == expected

    def test_color8_token_bg_only(self) -> None:
        token = Color8Token(value='44', params=['44'])
        expected_bg = {
            'colour_type': ColourType.BG,
            'ice_colours': False,
            'original_value': '44',
            'value': '44',
            'value_map': COLOUR_8_BG_VALUES,
            'value_name': 'blue',
        }
        expected = {
            'bg_token': expected_bg,
            'bright_bg': False,
            'bright_fg': False,
            'fg_token': None,
            'ice_colours': False,
            'original_value': '44',
            'params': ['44'],
            'sgr_tokens': [],
            'tokens': [expected_bg],
            'value': '44',
            'value_map': {},
            'value_name': '',
        }
        assert asdict(token) == expected

    def test_color8_token_fg_and_bg(self) -> None:
        token = Color8Token(value='31;44', params=['31', '44'])
        expected_bg = {
            'colour_type': ColourType.BG,
            'ice_colours': False,
            'original_value': '44',
            'value': '44',
            'value_map': COLOUR_8_BG_VALUES,
            'value_name': 'blue',
        }
        expected_fg = {
            'bright': False,
            'colour_type': ColourType.FG,
            'original_value': '31',
            'value': '31',
            'value_map': COLOUR_8_FG_VALUES,
            'value_name': 'red',
        }

        expected = {
            'bg_token': expected_bg,
            'bright_bg': False,
            'bright_fg': False,
            'fg_token': expected_fg,
            'ice_colours': False,
            'original_value': '31;44',
            'params': ['31', '44'],
            'sgr_tokens': [],
            'tokens': [expected_fg, expected_bg],
            'value': '31;44',
            'value_map': {},
            'value_name': '',
        }

        assert asdict(token) == expected

    def test_color8_token_with_sgr(self) -> None:
        token = Color8Token(value='1;31', params=['1', '31'])
        expected_fg = {
            'value': '91',
            'original_value': '31',
            'value_name': 'red',
            'value_map': COLOUR_8_FG_VALUES,
            'colour_type': ColourType.FG,
            'bright': True,
        }
        expected_sgr = {
            'value': '1',
            'original_value': '1',
            'value_name': 'Bold',
            'value_map': SGR_CODES,
        }
        expected = {
            'bg_token': None,
            'bright_bg': False,
            'bright_fg': True,
            'fg_token': expected_fg,
            'ice_colours': False,
            'original_value': '1;31',
            'params': ['1', '31'],
            'sgr_tokens': [expected_sgr],
            'tokens': [expected_sgr, expected_fg],
            'value': '1;31',
            'value_map': {},
            'value_name': '',
        }
        assert asdict(token) == expected

    def test_color8_token_with_reset(self) -> None:
        token = Color8Token(value='0', params=['0'])
        expected_sgr = {
            'value': '0',
            'original_value': '0',
            'value_name': 'Reset',
            'value_map': SGR_CODES,
        }
        expected: dict = {
            'bg_token': None,
            'bright_bg': False,
            'bright_fg': False,
            'fg_token': None,
            'ice_colours': False,
            'original_value': '0',
            'params': ['0'],
            'sgr_tokens': [expected_sgr],
            'tokens': [expected_sgr],
            'value': '0',
            'value_map': {},
            'value_name': '',
        }
        assert asdict(token) == expected

    def test_color8_token_ice_colours(self) -> None:
        token = Color8Token(value='1;5;44', params=['1', '5', '44'], ice_colours=True)
        # With ice_colours, param '5' enables bright background
        expected_sgr = {
            'value': '1',
            'original_value': '1',
            'value_name': 'Bold',
            'value_map': SGR_CODES,
        }
        expected_bg = {
            'colour_type': ColourType.BG,
            'ice_colours': True,
            'original_value': '44',
            'value': '104',  # 44 + 60 = 104 (ice colours bright)
            'value_map': COLOUR_8_BG_VALUES,
            'value_name': 'blue',
        }
        expected = {
            'bg_token': expected_bg,
            'bright_bg': True,
            'bright_fg': True,
            'fg_token': None,
            'ice_colours': True,
            'original_value': '1;5;44',
            'params': ['1', '5', '44'],
            'sgr_tokens': [expected_sgr],
            'tokens': [expected_sgr, expected_bg],
            'value': '1;5;44',
            'value_map': {},
            'value_name': '',
        }
        assert asdict(token) == expected

    def test_color8_token_generate_tokens_basic(self) -> None:
        token = Color8Token(value='31;44', params=['31', '44'])
        result = list(token.generate_tokens(None, None))
        expected = [
            Color8FGToken(
                value='31',
                value_name='red',
                value_map=COLOUR_8_FG_VALUES,
                colour_type=ColourType.FG,
                bright=False,
            ),
            Color8BGToken(
                value='44',
                value_name='blue',
                value_map=COLOUR_8_BG_VALUES,
                colour_type=ColourType.BG,
                ice_colours=False,
            ),
        ]
        assert result == expected

    def test_color8_token_generate_tokens_with_reset(self) -> None:
        token = Color8Token(value='0;37;40', params=['0', '37', '40'])
        result = list(token.generate_tokens(None, None))
        expected = [
            SGRToken(
                value='0',
                value_name='Reset',
                value_map=SGR_CODES,
            ),
            Color8FGToken(
                value='37',
                value_name='white',
                value_map=COLOUR_8_FG_VALUES,
                colour_type=ColourType.FG,
                bright=False,
            ),
            Color8BGToken(
                value='40',
                value_name='black',
                value_map=COLOUR_8_BG_VALUES,
                colour_type=ColourType.BG,
                ice_colours=False,
            ),
        ]
        assert result == expected

    def test_color8_token_str(self) -> None:
        token = Color8Token(value='31;44', params=['31', '44'])
        assert str(token) == '\x1b[31;44m'


class TestSGRToken:
    'Test SGR (Select Graphic Rendition) tokens'

    def test_sgr_reset(self) -> None:
        token = SGRToken(value='0')
        expected = {
            'value': '0',
            'original_value': '0',
            'value_name': 'Reset',
            'value_map': SGR_CODES,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[0m'

    def test_sgr_bold(self) -> None:
        token = SGRToken(value='1')
        expected = {
            'value': '1',
            'original_value': '1',
            'value_name': 'Bold',
            'value_map': SGR_CODES,
        }
        assert asdict(token) == expected
        assert str(token) == '\x1b[1m'

    def test_sgr_dim(self) -> None:
        token = SGRToken(value='2')
        assert token.value_name == 'Dim'

    def test_sgr_italic(self) -> None:
        token = SGRToken(value='3')
        assert token.value_name == 'Italic'

    def test_sgr_underline(self) -> None:
        token = SGRToken(value='4')
        assert token.value_name == 'Underline'

    def test_sgr_blink_slow(self) -> None:
        token = SGRToken(value='5')
        assert token.value_name == 'BlinkSlow'

    def test_sgr_reverse_video(self) -> None:
        token = SGRToken(value='7')
        assert token.value_name == 'ReverseVideo'


class TestNewLineToken:
    'Test newline token'

    def test_newline_token(self) -> None:
        token = NewLineToken(value='\n')
        assert str(token) == '\n'


class TestEOFToken:
    'Test end-of-file token'

    def test_eof_token(self) -> None:
        token = EOFToken(value='')
        assert str(token) == ''


class TestUnknownToken:
    'Test unknown/unrecognized token'

    def test_unknown_token(self) -> None:
        token = UnknownToken(value='\x1b[999Z')
        assert token.value == '\x1b[999Z'
