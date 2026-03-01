#!/usr/bin/env python3
'Unit tests for Tokeniser class and tokenise() method in convert.py'

import pytest

from ansi_art_convert.convert import (
    C0Token,
    Color8Token,
    ControlToken,
    CP437Token,
    NewLineToken,
    TextToken,
    Tokeniser,
    TrueColorBGToken,
    TrueColorFGToken,
    UnknownToken,
    get_glyph_offset,
)
from ansi_art_convert.encoding import SupportedEncoding
from ansi_art_convert.sauce import SauceRecord, SauceRecordExtended


def create_mock_sauce(width: int = 80, ice_colours: bool = False, font_name: str = 'IBM VGA') -> SauceRecordExtended:
    'Helper to create mock SAUCE records for testing'

    return SauceRecordExtended(
        fpath='/test/file.ans',
        encoding=SupportedEncoding.CP437,
        sauce=SauceRecord(
            ID='SAUCE',
            version='00',
            title='Test',
            author='Author',
            group='Group',
            date='20240101',
            filesize=0,
            data_type=1,
            file_type=1,
            tinfo1=width,
            tinfo2=0,
            tinfo3=0,
            tinfo4=0,
            comments=0,
            flags=0 if not ice_colours else 1,
            tinfo_s=font_name,
        ),
        comments_data=[],
        font={'name': font_name},
        tinfo={},
        aspect_ratio='',
        letter_spacing='',
        non_blink_mode=ice_colours,
        ice_colours=ice_colours,
    )


class TestGetGlyphOffset:
    'Test glyph offset function'

    def test_unknown_font_raises_error(self) -> None:
        with pytest.raises(ValueError, match='Unknown font_name'):
            get_glyph_offset('NonExistentFont')


class TestTokeniserInit:
    'Test Tokeniser initialization'

    def test_tokeniser_sauce_width(self) -> None:
        sauce = create_mock_sauce(width=67)
        tokeniser = Tokeniser(
            fpath='/test/file.ans',
            sauce=sauce,
            data='Hello',
            font_name='IBM VGA',
        )
        assert tokeniser.width == sauce.sauce.tinfo1

    def test_tokeniser_custom_width(self) -> None:
        sauce = create_mock_sauce(width=40)
        tokeniser = Tokeniser(
            fpath='/test/file.ans',
            sauce=sauce,
            data='Hello',
            font_name='IBM VGA',
            width=100,
        )
        assert tokeniser.width == 100  # Explicit width overrides sauce

    def test_tokeniser_ice_colours(self) -> None:
        sauce = create_mock_sauce(ice_colours=True)
        tokeniser = Tokeniser(
            fpath='/test/file.ans',
            sauce=sauce,
            data='Hello',
            font_name='IBM VGA',
        )
        assert tokeniser.ice_colours is True


class TestTokeniserCreateTokens:
    'Test create_tokens method'

    def setup_class(self) -> None:
        self.sauce = create_mock_sauce()
        self.tokeniser = Tokeniser(
            fpath='/test/file.ans',
            sauce=self.sauce,
            data='',
            font_name='IBM VGA',
        )

    def test_create_color_token(self) -> None:
        result = self.tokeniser.create_tokens(list('\x1b[31m'))
        expected = [
            Color8Token(
                value='31',
                params=['31'],
            )
        ]
        assert result == expected

    def test_create_color_token_multiple_params(self) -> None:
        result = self.tokeniser.create_tokens(list('\x1b[1;31m'))
        expected = [
            Color8Token(
                value='1;31',
                params=['1', '31'],
            )
        ]
        assert result == expected

    def test_create_cursor_up_token(self) -> None:
        result = self.tokeniser.create_tokens(['\x1b', '[', '5', 'A'])
        expected = [
            ControlToken(
                value='\x1b[5A',
            )
        ]
        assert result == expected

    def test_create_true_color_fg_token(self) -> None:
        result = self.tokeniser.create_tokens(['\x1b', '[', '1', ';', '255', ';', '128', ';', '64', 't'])
        expected = [
            TrueColorFGToken(
                value='255,128,64',
            )
        ]
        assert result == expected

    def test_create_true_color_bg_token(self) -> None:
        result = self.tokeniser.create_tokens(['\x1b', '[', '0', ';', '0', ';', '255', ';', '128', 't'])
        expected = [
            TrueColorBGToken(
                value='0,255,128',
            )
        ]
        assert result == expected

    def test_create_unknown_token(self) -> None:
        result = self.tokeniser.create_tokens(['\x1b', '[', '9', '9', '9', 'Z'])
        expected = [
            UnknownToken(
                value='\x1b[999Z',
            )
        ]
        assert result == expected

    def test_create_token_too_short(self) -> None:
        result = self.tokeniser.create_tokens(['\x1b'])
        expected = [
            UnknownToken(
                value='\x1b',
            )
        ]
        assert result == expected


class TestTokeniserTokenise:
    'Test tokenise method - main tokenization logic'

    def setup_class(self) -> None:
        self.sauce = create_mock_sauce()
        self.tokeniser = Tokeniser(
            fpath='/test/file.ans',
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
            Color8Token(value='31', params=['31']),
            CP437Token(value='Red', offset=self.tokeniser.glyph_offset),
            Color8Token(value='0', params=['0']),
        ]
        assert result == expected

    def test_tokenise_multiple_colors(self) -> None:
        self.tokeniser.data = '\x1b[31mRed\x1b[32mGreen\x1b[34mBlue'
        result = list(self.tokeniser.tokenise())
        expected = [
            Color8Token(value='31', params=['31']),
            CP437Token(value='Red', offset=self.tokeniser.glyph_offset),
            Color8Token(value='32', params=['32']),
            CP437Token(value='Green', offset=self.tokeniser.glyph_offset),
            Color8Token(value='34', params=['34']),
            CP437Token(value='Blue', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_with_control_sequences(self) -> None:
        self.tokeniser.data = 'Hello\x1b[5CWorld'
        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='Hello', offset=self.tokeniser.glyph_offset),
            ControlToken(value='\x1b[5C'),
            CP437Token(value='World', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_c0_character(self) -> None:
        self.tokeniser.data = 'Hello\rWorld'
        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='Hello', offset=self.tokeniser.glyph_offset),
            C0Token(value='\r', value_name='CR', offset=self.tokeniser.glyph_offset),
            CP437Token(value='World', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_empty_string(self) -> None:
        self.tokeniser.data = ''
        result = list(self.tokeniser.tokenise())
        expected: list = list()
        assert result == expected

    def test_tokenise_only_ansi_codes(self) -> None:
        self.tokeniser.data = '\x1b[31m\x1b[44m\x1b[1m'
        result = list(self.tokeniser.tokenise())
        expected = [
            Color8Token(value='31', params=['31']),
            Color8Token(value='44', params=['44']),
            Color8Token(value='1', params=['1']),
        ]
        assert result == expected

    def test_tokenise_mixed_content(self) -> None:
        complex_data = '\x1b[31mRed\x1b[0m\nNormal\x1b[1;32mBold Green\x1b[10CSpaced'
        self.tokeniser.data = complex_data
        result = list(self.tokeniser.tokenise())
        expected = [
            Color8Token(value='31', params=['31']),
            CP437Token(value='Red', offset=self.tokeniser.glyph_offset),
            Color8Token(value='0', params=['0']),
            NewLineToken(value='\n'),
            CP437Token(value='Normal', offset=self.tokeniser.glyph_offset),
            Color8Token(value='1;32', params=['1', '32']),
            CP437Token(value='Bold Green', offset=self.tokeniser.glyph_offset),
            ControlToken(value='\x1b[10C'),
            CP437Token(value='Spaced', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_utf8_encoding(self) -> None:
        tokeniser = Tokeniser(
            fpath='/test/file.ans',
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
            C0Token(value='\t', value_name='HT', offset=self.tokeniser.glyph_offset),
            CP437Token(value='World', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_cursor_position(self) -> None:
        self.tokeniser.data = '\x1b[10;20HText'
        result = list(self.tokeniser.tokenise())
        expected = [
            ControlToken(value='\x1b[10;20H'),
            CP437Token(value='Text', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_tokenise_preserves_order(self) -> None:
        self.tokeniser.data = 'A\x1b[31mB\nC'
        result = list(self.tokeniser.tokenise())
        expected = [
            CP437Token(value='A', offset=self.tokeniser.glyph_offset),
            Color8Token(value='31', params=['31']),
            CP437Token(value='B', offset=self.tokeniser.glyph_offset),
            NewLineToken(value='\n'),
            CP437Token(value='C', offset=self.tokeniser.glyph_offset),
        ]
        assert result == expected
