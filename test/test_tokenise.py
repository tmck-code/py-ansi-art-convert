#!/usr/bin/env python3
'Unit tests for Tokeniser class and tokenise() method in convert.py'

from dataclasses import asdict

import pytest

from ansi_art_convert.convert import (
    C0Token,
    Color8BGToken,
    Color8FGToken,
    Color256BGToken,
    Color256FGToken,
    ColorToken,
    ColourType,
    ControlToken,
    CP437Token,
    NewLineToken,
    SGRToken,
    TextToken,
    Tokeniser,
    TrueColorBGToken,
    TrueColorFGToken,
    UnknownToken,
    get_glyph_offset,
    set_glyph_offset,
)
from ansi_art_convert.encoding import SupportedEncoding
from test.helper import create_mock_sauce


class TokeniserTest:
    def setup_class(self) -> None:
        self.sauce = create_mock_sauce()
        self.tokeniser = Tokeniser(
            sauce=self.sauce,
            data='',
            font_name='IBM VGA',
        )


class TestGetGlyphOffset:
    'Test glyph offset function'

    def test_unknown_font_raises_error(self) -> None:
        with pytest.raises(ValueError, match='Unknown font_name'):
            get_glyph_offset('NonExistentFont')


class TestTokeniserInit:
    'Test Tokeniser initialization'

    def test_tokeniser_ice_colours(self) -> None:
        sauce = create_mock_sauce(extended_kwargs={'non_blink_mode': True})

        tokeniser = Tokeniser(
            sauce=sauce,
            data='Hello',
            font_name='IBM VGA',
        )
        assert tokeniser.ice_colours is True

    def test_tokeniser_glyph_offset(self) -> None:
        tokeniser = Tokeniser(
            sauce=create_mock_sauce(),
            data='Hello',
            font_name='IBM VGA',
        )
        expected_offset = 0xE800
        assert tokeniser.glyph_offset == expected_offset

    def test_tokeniser_glyph_offset_override(self) -> None:
        tokeniser = Tokeniser(
            sauce=create_mock_sauce(),
            data='Hello',
            font_name='IBM VGA',
            glyph_offset=0xE200,
        )
        assert tokeniser._textTokenType._offset == 0xE200

    def test_tokeniser_text_token_type_cp437(self) -> None:
        tokeniser = Tokeniser(
            sauce=create_mock_sauce(),
            data='Hello',
            font_name='IBM VGA',
            encoding=SupportedEncoding.CP437,
        )
        assert tokeniser._textTokenType == CP437Token

    def test_tokeniser_text_token_type_utf8(self) -> None:
        tokeniser_utf8 = Tokeniser(
            sauce=create_mock_sauce(),
            data='Hello',
            font_name='IBM VGA',
            encoding=SupportedEncoding.UTF_8,
        )
        assert tokeniser_utf8._textTokenType == TextToken

    def test_tokeniser_text_token_type_iso8859_1(self) -> None:
        tokeniser_iso = Tokeniser(
            sauce=create_mock_sauce(),
            data='Hello',
            font_name='IBM VGA',
            encoding=SupportedEncoding.ISO_8859_1,
        )
        assert tokeniser_iso._textTokenType == TextToken


class TestTokeniserColourTokens:
    'Test create_tokens method'

    def setup_class(self) -> None:
        self.sauce = create_mock_sauce()
        self.tokeniser = Tokeniser(
            sauce=self.sauce,
            data='',
            font_name='IBM VGA',
        )

    def test_create_color_token(self) -> None:
        result = self.tokeniser.create_token('\x1b[31', 'm')
        expected = ColorToken(
            value='31',
            sgr_token=None,
            fg_token=Color8FGToken(value='31', bright=False),
            bg_token=None,
        )
        assert result.value == expected.value
        assert asdict(result) == asdict(expected)

    def test_create_color_token_multiple_params(self) -> None:
        result = self.tokeniser.create_token('\x1b[1;31', 'm')
        expected = ColorToken(
            value='1;31',
            sgr_token=SGRToken(value='1'),
            fg_token=Color8FGToken(value='31', bright=True),
            bg_token=None,
        )

        assert result.value == expected.value
        assert asdict(result) == asdict(expected)

    def test_create_true_color_fg_token(self) -> None:
        result = self.tokeniser.create_token('\x1b[1;255;128;64', 't')
        expected = TrueColorFGToken(value='1;255;128;64')
        assert result == expected

    def test_create_true_color_bg_token(self) -> None:
        result = self.tokeniser.create_token('\x1b[0;0;255;128', 't')
        expected = TrueColorBGToken(value='0;0;255;128')
        assert result == expected

    def test_create_256_color_fg_token(self) -> None:
        result = self.tokeniser.create_token('\x1b[38;5;123', 'm')
        expected = Color256FGToken(value='123')
        assert result == expected

    def test_create_256_color_bg_token(self) -> None:
        result = self.tokeniser.create_token('\x1b[48;5;45', 'm')
        expected = Color256BGToken(value='45')
        assert result == expected


class TestTokeniseUnknown(TokeniserTest):
    def test_create_unknown_token(self) -> None:
        result = self.tokeniser.create_token('\x1b[999Z', '')
        expected = UnknownToken(value='\x1b[999Z')
        assert result == expected

    def test_create_token_too_short(self) -> None:
        result = self.tokeniser.create_token('\x1b', '')
        expected = UnknownToken(value='\x1b')
        assert result == expected


class TestTokeniserTokenise:
    'Test tokenise method - main tokenization logic'

    def setup_method(self) -> None:
        self.sauce = create_mock_sauce()
        self.tokeniser = Tokeniser(
            sauce=self.sauce,
            data='',
            font_name='IBM VGA',
        )

    def test_tokenise_simple_text(self) -> None:
        self.tokeniser.data = 'Hello'
        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='Hello', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_text_with_newline(self) -> None:
        self.tokeniser.data = 'Hello\nWorld'
        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='Hello', offset=self.tokeniser.glyph_offset),
            NewLineToken(value='\n'),
            CP437Token(value='World', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_text_with_color(self) -> None:
        self.tokeniser.data = '\x1b[31mRed\x1b[0m'
        result = list(self.tokeniser.tokenise())
        expected = [
            ColorToken(
                value='31',
                fg_token=Color8FGToken(value='31', bright=False),
            ),
            CP437Token(value='Red', offset=self.tokeniser.glyph_offset),
            ColorToken(
                value='0',
                sgr_token=SGRToken(value='0'),
            ),
        ]
        assert result == expected

    def test_tokenise_multiple_colors(self) -> None:
        self.tokeniser.data = '\x1b[31mRed\x1b[32mGreen\x1b[34mBlue'
        result = list(self.tokeniser.tokenise())
        expected = [
            ColorToken(
                value='31',
                fg_token=Color8FGToken(value='31', bright=False),
            ),
            CP437Token(value='Red', offset=self.tokeniser.glyph_offset),
            ColorToken(
                value='32',
                fg_token=Color8FGToken(value='32', bright=False),
            ),
            CP437Token(value='Green', offset=self.tokeniser.glyph_offset),
            ColorToken(
                value='34',
                fg_token=Color8FGToken(value='34', bright=False),
            ),
            CP437Token(value='Blue', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_with_control_sequences(self) -> None:
        self.tokeniser.data = 'Hello\x1b[5CWorld'
        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='Hello', offset=self.tokeniser.glyph_offset),
            ControlToken(value='5C'),
            CP437Token(value='World', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_c0_character(self) -> None:
        self.tokeniser.data = 'Hello\rWorld'
        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='Hello', offset=self.tokeniser.glyph_offset),
            C0Token(value='\r'),
            CP437Token(value='World', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_empty_string(self) -> None:
        self.tokeniser.data = ''
        result = list(self.tokeniser.tokenise())
        assert result == []

    def test_tokenise_only_ansi_codes(self) -> None:
        self.tokeniser.data = '\x1b[31m\x1b[44m\x1b[1m'
        result = list(self.tokeniser.tokenise())
        expected = [
            ColorToken(
                value='31',
                fg_token=Color8FGToken(value='31', bright=False),
            ),
            ColorToken(
                value='44',
                bg_token=Color8BGToken(value='44', bright=False),
            ),
            ColorToken(
                value='1',
                sgr_token=SGRToken(value='1'),
            ),
        ]
        assert result == expected

    def test_tokenise_mixed_content(self) -> None:
        complex_data = '\x1b[31mRed\x1b[0m\nNormal\x1b[1;32mBold Green\x1b[10CSpaced'
        self.tokeniser.data = complex_data
        result = list(self.tokeniser.tokenise())
        expected = [
            ColorToken(
                value='31',
                fg_token=Color8FGToken(value='31', bright=False),
            ),
            CP437Token(value='Red', offset=self.tokeniser.glyph_offset),
            ColorToken(
                value='0',
                sgr_token=SGRToken(value='0'),
            ),
            NewLineToken(value='\n'),
            CP437Token(value='Normal', offset=self.tokeniser.glyph_offset),
            ColorToken(
                value='1;32',
                sgr_token=SGRToken(value='1'),
                fg_token=Color8FGToken(value='32', bright=True),
            ),
            CP437Token(value='Bold Green', offset=self.tokeniser.glyph_offset),
            ControlToken(value='10C'),
            CP437Token(value='Spaced', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_utf8_encoding(self) -> None:
        tokeniser = Tokeniser(
            sauce=create_mock_sauce(),
            data='Hello ♥ World',
            font_name='IBM VGA',
            encoding=SupportedEncoding.UTF_8,
        )
        result = list(tokeniser.tokenise())
        expected = [
            TextToken(value='Hello ♥ World', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_with_tab(self) -> None:
        self.tokeniser.data = 'Hello\tWorld'
        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='Hello', offset=self.tokeniser.glyph_offset),
            C0Token(value='\t'),
            CP437Token(value='World', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_cursor_position(self) -> None:
        self.tokeniser.data = '\x1b[10;20HText'
        result = [(type(t), asdict(t)) for t in self.tokeniser.tokenise()]
        expected = [
            (ControlToken, {'value': '10;20', 'value_name': 'CursorPosition', 'subtype': 'H'}),
            (CP437Token, {'value': 'Text', 'offset': self.tokeniser.glyph_offset}),
        ]
        assert result == expected

    def test_create_cursor_up_token(self) -> None:
        self.tokeniser.data = '\x1b[5A'
        result = [(type(t), asdict(t)) for t in self.tokeniser.tokenise()]
        expected = [
            (ControlToken, {'value': '5', 'value_name': 'CursorUp', 'subtype': 'A'}),
        ]
        assert result == expected

    def test_tokenise_preserves_order(self) -> None:
        self.tokeniser.data = 'A\x1b[31mB\nC'
        result = [(type(t), asdict(t)) for t in self.tokeniser.tokenise()]
        expected = [
            (CP437Token, {'value': 'A', 'offset': self.tokeniser.glyph_offset}),
            (
                ColorToken,
                {
                    'value': '31',
                    'fg_token': {
                        'value': '31',
                        'colour_type': ColourType.FG,
                        'value_name': 'red',
                        'bright': False,
                    },
                    'bg_token': None,
                    'sgr_token': None,
                    'ice_colour_mode': False,
                    'parts': ['31'],
                },
            ),
            (CP437Token, {'value': 'B', 'offset': self.tokeniser.glyph_offset}),
            (NewLineToken, {'value': '\n'}),
            (CP437Token, {'value': 'C', 'offset': self.tokeniser.glyph_offset}),
        ]
        assert result == expected


class TestSaveRestoreCursor:
    'Test SaveCursorPosition (ESC[s) and RestoreCursorPosition (ESC[u) support'

    def setup_method(self) -> None:
        self.sauce = create_mock_sauce()
        self.tokeniser = Tokeniser(
            sauce=self.sauce,
            data='',
            font_name='IBM VGA',
        )
        self.offset = 0
        set_glyph_offset(self.offset)

        self.save, self.restore = '\x1b[s', '\x1b[u'
        self.save_token, self.restore_token = ControlToken(value='s'), ControlToken(value='u')

    def test_tokenise_save(self) -> None:
        self.tokeniser.data = f'Hello{self.save} World'

        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='Hello', offset=self.offset),
            self.save_token,
            CP437Token(value=' World', offset=self.offset),
        ]
        assert result == expected

    def test_tokenise_save_restore(self) -> None:
        # Hello\x1b[s World\x1b[u! > Hello!World
        self.tokeniser.data = f'Hello{self.save} World{self.restore}!'

        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='Hello', offset=self.offset),
            self.save_token,
            CP437Token(value=' World', offset=self.offset),
            self.restore_token,
            CP437Token(value='!', offset=self.offset),
        ]
        assert result == expected

    def test_tokenise_restore(self) -> None:
        # Hello\x1b[s World\x1b[u! > Hello!World
        self.tokeniser.data = f'Hello{self.save} World{self.restore}!'

        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='Hello', offset=self.offset),
            self.save_token,
            CP437Token(value=' World', offset=self.offset),
            self.restore_token,
            CP437Token(value='!', offset=self.offset),
        ]
        assert result == expected

    def test_newlines(self) -> None:
        data = ''.join([
            f'AAAA{self.save}\n',
            f'{self.restore}▓▒░',
        ])
        self.tokeniser.data = data

        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='AAAA', offset=self.offset),
            self.save_token,
            NewLineToken(value='\n'),
            self.restore_token,
            CP437Token(value='▓▒░', offset=self.offset),
        ]
        assert result == expected

    def test_width(self) -> None:
        data = ''.join([
            f'AAAA{self.save}\n',
            f'{self.restore}▓▒░{self.save}\n',
            f'{self.restore}XXXXXXX\n',
        ])
        self.tokeniser.data = data

        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='AAAA', offset=self.offset),
            self.save_token,
            NewLineToken(value='\n'),
            self.restore_token,
            CP437Token(value='▓▒░', offset=self.offset),
            self.save_token,
            NewLineToken(value='\n'),
            self.restore_token,
            CP437Token(value='XXXXXXX', offset=self.offset),
            NewLineToken(value='\n'),
        ]
        assert result == expected
