#!/usr/bin/env python3
'Unit tests for Renderer class, gen_lines() and render() methods in convert.py'

from dataclasses import asdict
from itertools import batched

from ansi_art_convert.convert import (
    ANSIToken,
    ColorToken,
    ColourType,
    ControlToken,
    EOFToken,
    Renderer,
    TextToken,
    set_glyph_offset,
)
from test.helper import create_renderer, create_tokeniser


class TestRenderer:
    'Test Renderer initialization'

    def setup_class(self) -> None:
        self.tokeniser = create_tokeniser('Hello')

    def test_renderer_basic_init(self) -> None:
        renderer = Renderer(fpath='/test/file.ans', tokeniser=self.tokeniser)
        assert renderer.fpath == '/test/file.ans'
        assert renderer.tokeniser == self.tokeniser
        assert renderer.width == 80

    def test_renderer_custom_width(self) -> None:
        renderer = Renderer(fpath='/test/file.ans', tokeniser=self.tokeniser)
        assert renderer.width == 40


class TestSplitTextToken:
    'Test split_text_token method for line wrapping'

    def setup_method(self) -> None:
        self.offset = 0
        self.renderer = Renderer(fpath='/test/file.ans', tokeniser=create_tokeniser())
        set_glyph_offset(self.offset)

    def test_split_exact_multiple(self) -> None:
        self.renderer.width = 5
        s = 'HelloWorldAbcde'  # string is length 15

        result = list(self.renderer.split_text_token(TextToken(value=s, offset=self.offset)))

        chunks = list(map(''.join, batched(s, 5)))
        expected = [
            TextToken(value=chunks[0], offset=self.offset),
            TextToken(value=chunks[1], offset=self.offset),
            TextToken(value=chunks[2], offset=self.offset),
        ]
        assert result == expected

    def test_split_multiple_chunks(self) -> None:
        self.renderer.width = 5

        token = TextToken(value='A' * 25, offset=self.offset)

        result = list(self.renderer.split_text_token(token))
        expected = [TextToken(value='A' * 5, offset=self.offset)] * 5
        assert result == expected

    def test_split_no_split(self) -> None:
        self.renderer.width = 80

        token = TextToken(value='Hi', offset=self.offset)

        result = list(self.renderer.split_text_token(token))
        expected = [token]
        assert result == expected

    def test_split_exact_width(self) -> None:
        self.renderer.width = 5

        token = TextToken(value='Hello', offset=self.offset)

        result = list(self.renderer.split_text_token(token))
        expected = [token]
        assert result == expected


class TestGrid:
    def setup_method(self) -> None:
        self.offset = 0
        self.renderer = create_renderer('')
        set_glyph_offset(self.offset)

    def gather_results(self, grid: list[list[ANSIToken]]) -> list[list[tuple[type, dict]]]:
        result = []
        for line in grid:
            resultLine = []
            for el in line:
                resultLine.append((type(el), asdict(el)))
            result.append(resultLine)
        return result

    def test_simple_text(self) -> None:
        self.renderer.tokeniser.data = 'Hello'

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [(TextToken, {'value': 'Hello', 'offset': 0})],
        ]
        assert result == expected

    def test_text_with_newline(self) -> None:
        self.renderer.tokeniser.data = 'Hello\nWorld'

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [(TextToken, {'value': 'Hello', 'offset': 0})],
            [(TextToken, {'value': 'World', 'offset': 0})],
        ]
        assert result == expected

    def test_text_at_width_boundary(self) -> None:
        self.renderer.tokeniser.data = 'A' * 80

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [(TextToken, {'value': 'A' * 80, 'offset': 0})],
        ]
        assert result == expected

    def test_text_exceeds_width(self) -> None:
        self.renderer.tokeniser.data = 'A' * 100

        tokens = list(self.renderer.tokeniser.tokenise())
        expected_tokens = [
            TextToken(value='A' * 100, offset=self.offset),
        ]
        assert tokens == expected_tokens

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [(TextToken, {'value': 'A' * 80, 'offset': 0})],
            [(TextToken, {'value': 'A' * 20, 'offset': 0})],
        ]

        assert result == expected

    def test_with_colours(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31mRed\x1b[0m'

        result = self.gather_results(list(self.renderer.grid()))

        expected = [
            [
                (
                    ColorToken,
                    {
                        'value': '31',
                        'ice_colour_mode': False,
                        'parts': ['31'],
                        'sgr_token': None,
                        'fg_token': {
                            'colour_type': ColourType.FG,
                            'value': '31',
                            'value_name': 'red',
                            'bright': False,
                        },
                        'bg_token': None,
                    },
                ),
                (TextToken, {'value': 'Red', 'offset': 0}),
                (
                    ColorToken,
                    {
                        'value': '0',
                        'ice_colour_mode': False,
                        'parts': ['0'],
                        'sgr_token': {'value': '0', 'value_name': 'Reset'},
                        'fg_token': None,
                        'bg_token': None,
                    },
                ),
            ]
        ]
        assert result == expected

    def test_preserves_colors_across_wraps(self) -> None:
        # When text wraps, colors should be preserved on the next line
        data = '\x1b[31m' + 'A' * 90 + '\x1b[0m'
        self.renderer.tokeniser.data = data

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [
                (
                    ColorToken,
                    {
                        'value': '31',
                        'ice_colour_mode': False,
                        'parts': ['31'],
                        'sgr_token': None,
                        'fg_token': {
                            'colour_type': ColourType.FG,
                            'value': '31',
                            'value_name': 'red',
                            'bright': False,
                        },
                        'bg_token': None,
                    },
                ),
                (TextToken, {'value': 'A' * 80, 'offset': 0}),
            ],
            [
                (TextToken, {'value': 'A' * 10, 'offset': 0}),
                (
                    ColorToken,
                    {
                        'value': '0',
                        'ice_colour_mode': False,
                        'parts': ['0'],
                        'sgr_token': {'value': '0', 'value_name': 'Reset'},
                        'fg_token': None,
                        'bg_token': None,
                    },
                ),
            ],
        ]
        assert result == expected

    def test_color_reset_clears_state(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31mRed\x1b[0mNormal'

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [
                (
                    ColorToken,
                    {
                        'value': '31',
                        'ice_colour_mode': False,
                        'parts': ['31'],
                        'sgr_token': None,
                        'fg_token': {
                            'colour_type': ColourType.FG,
                            'value': '31',
                            'value_name': 'red',
                            'bright': False,
                        },
                        'bg_token': None,
                    },
                ),
                (TextToken, {'value': 'Red', 'offset': 0}),
                (
                    ColorToken,
                    {
                        'value': '0',
                        'ice_colour_mode': False,
                        'parts': ['0'],
                        'sgr_token': {'value': '0', 'value_name': 'Reset'},
                        'fg_token': None,
                        'bg_token': None,
                    },
                ),
                (TextToken, {'value': 'Normal', 'offset': 0}),
            ]
        ]
        assert result == expected

    def test_multiple_colors(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31mRed\x1b[32mGreen\x1b[34mBlue'

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [
                (
                    ColorToken,
                    {
                        'value': '31',
                        'ice_colour_mode': False,
                        'parts': ['31'],
                        'sgr_token': None,
                        'fg_token': {
                            'colour_type': ColourType.FG,
                            'value': '31',
                            'value_name': 'red',
                            'bright': False,
                        },
                        'bg_token': None,
                    },
                ),
                (TextToken, {'value': 'Red', 'offset': 0}),
                (
                    ColorToken,
                    {
                        'value': '32',
                        'ice_colour_mode': False,
                        'parts': ['32'],
                        'sgr_token': None,
                        'fg_token': {
                            'colour_type': ColourType.FG,
                            'value': '32',
                            'value_name': 'green',
                            'bright': False,
                        },
                        'bg_token': None,
                    },
                ),
                (TextToken, {'value': 'Green', 'offset': 0}),
                (
                    ColorToken,
                    {
                        'value': '34',
                        'ice_colour_mode': False,
                        'parts': ['34'],
                        'sgr_token': None,
                        'fg_token': {
                            'colour_type': ColourType.FG,
                            'value': '34',
                            'value_name': 'blue',
                            'bright': False,
                        },
                        'bg_token': None,
                    },
                ),
                (TextToken, {'value': 'Blue', 'offset': 0}),
            ]
        ]
        assert result == expected

    def test_empty_input(self) -> None:
        self.renderer.tokeniser.data = ''

        result = list(self.renderer.grid())
        assert result == []

    def test_control_sequences(self) -> None:
        self.renderer.tokeniser.data = 'Hello\x1b[5CWorld'

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [
                (TextToken, {'value': 'Hello', 'offset': 0}),
                (ControlToken, {'value': '5', 'value_name': 'CursorForward', 'subtype': 'C'}),
                (TextToken, {'value': 'World', 'offset': 0}),
            ]
        ]
        assert result == expected

    def test_cursor_position_clears_line(self) -> None:
        self.renderer.tokeniser.data = 'Hello\x1b[10;20HWorld'

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [
                (TextToken, {'value': 'Hello', 'offset': 0}),
                (ControlToken, {'value': '10;20', 'value_name': 'CursorPosition', 'subtype': 'H'}),
                (TextToken, {'value': 'World', 'offset': 0}),
            ]
        ]
        assert result == expected

    def test_width_20(self) -> None:
        self.renderer.tokeniser.data = 'HelloWorldThisIsATest'
        self.renderer.width = 20

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [(TextToken, {'value': 'HelloWorldThisIsATes', 'offset': 0})],
            [(TextToken, {'value': 't', 'offset': 0})],
        ]
        assert result == expected

    def test_fg_and_bg_colors(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31;44mColoredText\x1b[0m'

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [
                (
                    ColorToken,
                    {
                        'value': '31;44',
                        'ice_colour_mode': False,
                        'parts': ['31', '44'],
                        'sgr_token': None,
                        'fg_token': {
                            'colour_type': ColourType.FG,
                            'value': '31',
                            'value_name': 'red',
                            'bright': False,
                        },
                        'bg_token': {
                            'colour_type': ColourType.BG,
                            'value': '44',
                            'value_name': 'blue',
                            'bright': False,
                        },
                    },
                ),
                (TextToken, {'value': 'ColoredText', 'offset': 0}),
                (
                    ColorToken,
                    {
                        'value': '0',
                        'ice_colour_mode': False,
                        'parts': ['0'],
                        'sgr_token': {'value': '0', 'value_name': 'Reset'},
                        'fg_token': None,
                        'bg_token': None,
                    },
                ),
            ]
        ]
        assert result == expected

    def test_ice_colours(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31;44mText'
        self.renderer.tokeniser.ice_colours = True

        result = self.gather_results(list(self.renderer.grid()))
        expected = [
            [
                (
                    ColorToken,
                    {
                        'value': '31;44',
                        'ice_colour_mode': True,
                        'parts': ['31', '44'],
                        'sgr_token': None,
                        'fg_token': {
                            'colour_type': ColourType.FG,
                            'value': '31',
                            'value_name': 'red',
                            'bright': False,
                        },
                        'bg_token': {
                            'colour_type': ColourType.BG,
                            'value': '44',
                            'value_name': 'blue',
                            'bright': False,
                        },
                    },
                ),
                (TextToken, {'value': 'Text', 'offset': 0}),
            ]
        ]
        assert result == expected


class TestIterLines:
    'Test iter_lines method - converts token lines to strings'

    def setup_method(self) -> None:
        self.offset = 0
        self.renderer = create_renderer(data='')
        set_glyph_offset(self.offset)

    def test_iter_lines_simple(self) -> None:
        self.renderer.tokeniser.data = 'Hello'

        result = list(self.renderer.iter_lines())
        expected = [
            TextToken._translate_chars('Hello', self.offset) + '\x1b[0m\n',
            str(EOFToken(value='')),
        ]

        assert result == expected

    def test_iter_lines_multiple_lines(self) -> None:
        self.renderer.tokeniser.data = 'Hello\nWorld'

        result = list(self.renderer.iter_lines())
        expected = [
            TextToken._translate_chars('Hello', self.offset) + '\x1b[0m\n',
            TextToken._translate_chars('World', self.offset) + '\x1b[0m\n',
            str(EOFToken(value='')),
        ]
        assert result == expected

    def test_iter_lines_with_colors(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31mRed\x1b[0m'

        result = list(self.renderer.iter_lines())
        expected = [
            '\x1b[31m\x1b[40m' + TextToken._translate_chars('Red', self.offset) + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m\n',
            str(EOFToken(value='')),
        ]
        assert result == expected

    def test_iter_lines_preserves_reset(self) -> None:
        self.renderer.tokeniser.data = 'Test'

        result = list(self.renderer.iter_lines())
        expected = [
            TextToken._translate_chars('Test', self.offset) + '\x1b[0m\n',
            str(EOFToken(value='')),
        ]
        assert result == expected


class TestRender:
    'Test render method - combines all lines into final output'

    def setup_method(self) -> None:
        self.renderer = create_renderer(data='')
        self.offset = 0
        set_glyph_offset(self.offset)

    def test_render_simple_text(self) -> None:
        self.renderer.tokeniser.data = 'Hello World'

        result = self.renderer.render()
        expected = TextToken._translate_chars('Hello World', self.offset) + '\x1b[0m\n'
        assert result == expected

    def test_render_with_newlines(self) -> None:
        self.renderer.tokeniser.data = 'Hello\nWorld'

        result = self.renderer.render()
        expected = (
            TextToken._translate_chars('Hello', self.offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('World', self.offset)
            + '\x1b[0m\n'
        )
        assert result == expected

    def test_render_with_colors(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31mRed\x1b[32mGreen\x1b[0m'

        result = self.renderer.render()
        expected = (
            '\x1b[31m\x1b[40m'
            + TextToken._translate_chars('Red', self.offset)
            + '\x1b[32m\x1b[40m'
            + TextToken._translate_chars('Green', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m\n'
        )
        assert result == expected

    def test_render_long_text_wraps(self) -> None:
        self.renderer.tokeniser.data = 'A' * 100
        self.renderer.width = 100

        result = self.renderer.render()
        expected = TextToken._translate_chars('A' * 100, self.offset) + '\x1b[0m\n'
        assert result == expected

    def test_render_empty_input(self) -> None:
        self.renderer.tokeniser.data = ''

        result = self.renderer.render()
        expected = ''
        assert result == expected

    def test_render_complex_ansi_art(self) -> None:
        # Test with complex ANSI art-like content
        data = (
            '\x1b[31m╔══════════════════╗\x1b[0m\n'
            '\x1b[32m║  ANSI Art Test   ║\x1b[0m\n'
            '\x1b[34m╚══════════════════╝\x1b[0m'
        )
        self.renderer.tokeniser.data = data

        result = self.renderer.render()
        expected = (
            '\x1b[31m\x1b[40m'
            + TextToken._translate_chars('╔══════════════════╗', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m'
            + '\x1b[0m\n\x1b[37m\x1b[40m\x1b[32m\x1b[40m'
            + TextToken._translate_chars('║  ANSI Art Test   ║', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m'
            + '\x1b[0m\n\x1b[37m\x1b[40m\x1b[34m\x1b[40m'
            + TextToken._translate_chars('╚══════════════════╝', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m\n'
        )
        assert result == expected

    def test_render_preserves_color_state(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31m' + 'A' * 90 + '\x1b[0m'

        result = self.renderer.render()
        expected = (
            '\x1b[31m\x1b[40m'
            + TextToken._translate_chars('A' * 80, self.offset)
            + '\x1b[0m\n\x1b[31m\x1b[40m'
            + TextToken._translate_chars('A' * 10, self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m\n'
        )
        assert result == expected

    def test_render_ice_colours_mode(self) -> None:
        self.renderer.tokeniser.data = '\x1b[1;5;31;44mBright Text\x1b[0m'
        self.renderer.tokeniser.ice_colours = True

        result = self.renderer.render()
        expected = (
            '\x1b[1m\x1b[91m\x1b[104m'
            + TextToken._translate_chars('Bright Text', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m\n'
        )
        assert result == expected

    def test_render_no_trailing_garbage(self) -> None:
        self.renderer.tokeniser.data = 'Clean'

        result = self.renderer.render()
        expected = TextToken._translate_chars('Clean', self.offset) + '\x1b[0m\n'
        assert result == expected

    def test_render_handles_control_sequences(self) -> None:
        self.renderer.tokeniser.data = 'Start\x1b[10CMiddle\x1b[5CEnd'

        result = self.renderer.render()
        expected = (
            TextToken._translate_chars('Start', self.offset)
            + ' ' * 10
            + TextToken._translate_chars('Middle', self.offset)
            + ' ' * 5
            + TextToken._translate_chars('End', self.offset)
            + '\x1b[0m\n'
        )
        assert result == expected

    def test_render_multiple_resets(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31mRed\x1b[0m\x1b[32mGreen\x1b[0m\x1b[34mBlue\x1b[0m'

        result = self.renderer.render()
        expected = (
            '\x1b[31m\x1b[40m'
            + TextToken._translate_chars('Red', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[32m\x1b[40m'
            + TextToken._translate_chars('Green', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[34m\x1b[40m'
            + TextToken._translate_chars('Blue', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m\n'
        )
        assert result == expected

    def test_render_exact_width_boundary(self) -> None:
        self.renderer.tokeniser.data = 'X' * 80 + 'Y' * 80

        result = self.renderer.render()
        expected = (
            TextToken._translate_chars('X' * 80, self.offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('Y' * 80, self.offset)
            + '\x1b[0m\n'
        )
        assert result == expected

    def test_render_width_40(self) -> None:
        data = 'The quick brown fox jumps over the lazy dog'

        self.renderer.tokeniser.data = data
        self.renderer.width = 40

        result = list(self.renderer.iter_lines())
        expected = [
            TextToken._translate_chars(data[:40], self.offset) + '\x1b[0m\n',
            TextToken._translate_chars(data[40:], self.offset) + '\x1b[0m\n',
            '',
        ]
        assert result == expected


class TestRendererEdgeCases:
    'Test edge cases and special scenarios'

    def setup_method(self) -> None:
        self.offset = 0
        self.renderer = create_renderer(data='')
        set_glyph_offset(self.offset)

    def test_single_character(self) -> None:
        self.renderer.tokeniser.data = 'A'

        result = self.renderer.render()
        expected = TextToken._translate_chars('A', self.offset) + '\x1b[0m\n'
        assert result == expected

    def test_width_1(self) -> None:
        self.renderer.tokeniser.data = 'ABC'
        self.renderer.width = 1

        result = self.renderer.render()
        expected = (
            TextToken._translate_chars('A', self.offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('B', self.offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('C', self.offset)
            + '\x1b[0m\n'
        )
        assert result == expected

    def test_multiple_splits(self) -> None:
        data = 'X' * 22
        self.renderer.tokeniser.data = data
        self.renderer.width = 5

        result = self.renderer.render()
        expected = '\n'.join([
            TextToken._translate_chars('X' * 5, self.offset) + '\x1b[0m',
            TextToken._translate_chars('X' * 5, self.offset) + '\x1b[0m',
            TextToken._translate_chars('X' * 5, self.offset) + '\x1b[0m',
            TextToken._translate_chars('X' * 5, self.offset) + '\x1b[0m',
            TextToken._translate_chars('X' * 2, self.offset) + '\x1b[0m\n',
        ])
        assert result == expected

    # def test_consecutive_newlines(self) -> None:
    #     self.renderer.tokeniser.data = 'A\n\n\nB'

    #     result = self.renderer.render()
    #     expected = (
    #         TextToken._translate_chars('A', self.offset)
    #         + '\x1b[0m\n'
    #         + '\x1b[0m\n'
    #         + '\x1b[0m\n'
    #         + TextToken._translate_chars('B', self.offset)
    #         + '\x1b[0m\n'
    #     )
    #     assert result == expected

    def test_color_without_text(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31m\x1b[44m'

        result = self.renderer.render()
        expected = '\x1b[31m\x1b[40m\x1b[31m\x1b[44m\x1b[0m\n'
        assert result == expected

    def test_mixed_ansi_sequences(self) -> None:
        self.renderer.tokeniser.data = '\x1b[1m\x1b[31m\x1b[44mStyled\x1b[0m'

        result = self.renderer.render()
        expected = (
            '\x1b[1m\x1b[97m\x1b[40m\x1b[31m\x1b[40m\x1b[31m\x1b[44m'
            + TextToken._translate_chars('Styled', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m\n'
        )
        assert result == expected


class TestGridSaveRestoreCursor:
    'Test SaveCursorPosition (ESC[s) and RestoreCursorPosition (ESC[u) support'

    def setup_method(self) -> None:
        self.offset = 0
        self.renderer = create_renderer(data='', tokeniser_kwargs={'glyph_offset': self.offset})
        set_glyph_offset(self.offset)

        self.save, self.restore = '\x1b[s', '\x1b[u'
        self.save_token = ControlToken(value='s')
        self.restore_token = ControlToken(value='u')

    def test_tokenise_save(self) -> None:
        self.renderer.tokeniser.data = f'Hello{self.save} World'

        result = self.renderer.grid()
        expected = [
            [
                TextToken(value='Hello', offset=self.offset),
                self.save_token,
                TextToken(value=' World', offset=self.offset),
            ]
        ]
        assert result == expected

    def test_tokenise_save_restore(self) -> None:
        # Hello\x1b[s World\x1b[u! > Hello!World
        self.renderer.tokeniser.data = f'Hello{self.save} World{self.restore}!'

        result = self.renderer.grid()
        expected = [
            [
                TextToken(value='Hello', offset=self.offset),
                self.save_token,
                TextToken(value=' World', offset=self.offset),
                self.restore_token,
                TextToken(value='!', offset=self.offset),
            ]
        ]
        assert result == expected

    def test_tokenise_restore(self) -> None:
        # Hello\x1b[s World\x1b[u! > Hello!World
        self.renderer.tokeniser.data = f'Hello{self.save} World{self.restore}!'

        result = self.renderer.grid()
        expected = [
            [
                TextToken(value='Hello', offset=self.offset),
                self.save_token,
                TextToken(value=' World', offset=self.offset),
                self.restore_token,
                TextToken(value='!', offset=self.offset),
            ]
        ]
        assert result == expected

    def test_newlines(self) -> None:
        data = ''.join([
            f'AAAA{self.save}\n',
            f'{self.restore}▓▒░',
        ])
        self.renderer.tokeniser.data = data

        result = self.renderer.grid()
        expected = [
            [
                TextToken(value='AAAA', offset=0),
                self.save_token,
            ],
            [
                self.restore_token,
                TextToken(value='▓▒░', offset=0),
            ],
        ]

        assert result == expected

    def test_width(self) -> None:
        data = ''.join([
            f'AAAA{self.save}\n',
            f'{self.restore}▓▒░{self.save}\n',
            f'{self.restore}XXXXXXX\n',
        ])
        self.renderer.tokeniser.data = data

        result = self.renderer.grid()
        expected = [
            [
                TextToken(value='AAAA', offset=0),
                self.save_token,
            ],
            [
                self.restore_token,
                TextToken(value='▓▒░', offset=0),
                self.save_token,
            ],
            [
                self.restore_token,
                TextToken(value='XXXXXXX', offset=0),
            ],
        ]
        assert result == expected


class TestArrangeGrid:
    def setup_method(self) -> None:
        self.offset = 0
        self.renderer = create_renderer(data='', tokeniser_kwargs={'glyph_offset': self.offset})
        set_glyph_offset(self.offset)

        self.save, self.restore = '\x1b[s', '\x1b[u'
        self.save_token = ControlToken(value=self.save)
        self.restore_token = ControlToken(value=self.restore)

    def test_arrange_grid_save_restore(self) -> None:
        data = ''.join([
            f'AAAA{self.save}\r',
            f'{self.restore}▓▒░{self.save}\r',
            f'{self.restore}XXXXXXX\n',
        ])
        self.renderer.tokeniser.data = data

        grid = list(self.renderer.grid())
        result = list(self.renderer.arrange_grid(grid))
        expected = [
            [
                TextToken(value='AAAA', offset=0),
                TextToken(value='▓▒░', offset=0),
                TextToken(value='XXXXXXX', offset=0),
            ],
        ]
        assert result == expected


class TestRenderGrid:
    def setup_method(self) -> None:
        self.offset = 0
        self.renderer = create_renderer(data='', tokeniser_kwargs={'glyph_offset': self.offset})
        set_glyph_offset(self.offset)

        self.save, self.restore = '\x1b[s', '\x1b[u'
        self.save_token = ControlToken(value=self.save)
        self.restore_token = ControlToken(value=self.restore)

    def test_render_save_restore(self) -> None:
        data = ''.join([
            f'AAAA{self.save}\r',
            f'{self.restore}▓▒░{self.save}\r',
            f'{self.restore}XXXXXXX\n',
        ])
        self.renderer.tokeniser.data = data

        result = self.renderer.render()
        expected = 'AAAA▓▒░XXXXXXX\x1b[0m\n'
        assert result == expected

    def test_render_save_restore_wrap(self) -> None:
        data = ''.join([
            f'AAAAA{self.save}\r',  # 5 chars
            f'{self.restore}▓▒░▒▓{self.save}\r',  # also 5 chars
        ])
        self.renderer.tokeniser.data = data
        self.renderer.width = 6

        result = self.renderer.render()
        expected = (
            '''AAAAA▓\x1b[0m\n'''
            '''▒░▒▓\x1b[0m\n'''
        )
        assert result == expected
