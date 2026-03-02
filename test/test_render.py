#!/usr/bin/env python3
'Unit tests for Renderer class, gen_lines() and render() methods in convert.py'

from ansi_art_convert.convert import (
    Color8BGToken,
    Color8FGToken,
    ControlToken,
    EOFToken,
    NewLineToken,
    Renderer,
    SGRToken,
    TextToken,
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
        self.tokeniser.width = 40
        renderer = Renderer(fpath='/test/file.ans', tokeniser=self.tokeniser)
        assert renderer.width == 40


class TestSplitTextToken:
    'Test split_text_token method for line wrapping'

    def setup_method(self) -> None:
        self.renderer = Renderer(
            fpath='/test/file.ans',
            tokeniser=create_tokeniser(tokeniser_kwargs={'fpath': ''}),
        )
        self.offset = 0
        self.renderer.tokeniser.glyph_offset = self.offset

    def test_split_text_token_exact_fit(self) -> None:
        self.renderer.width = 5
        # Test splitting text that's exactly 15 chars with 5 char remainder
        result = list(
            self.renderer.split_text_token(
                TextToken(value='HelloWorldAbcde', offset=self.offset),
                remainder=5,
            )
        )
        s = ''.join(chr(ord(el) + self.offset) for el in 'HelloWorldAbcde')
        expected = [
            TextToken(value=s[:5], offset=self.offset),
            TextToken(value=s[5:10], offset=self.offset),
            TextToken(value=s[10:], offset=self.offset),
        ]
        assert result == expected

    def test_split_text_token_multiple_chunks(self) -> None:
        self.renderer.width = 5

        result = list(
            self.renderer.split_text_token(
                TextToken(value='A' * 25, offset=self.offset),
                remainder=self.renderer.width,
            )
        )
        expected = [
            TextToken(value='A' * 5, offset=self.offset),
        ] * 5
        assert result == expected

    def test_split_text_token_no_split(self) -> None:
        self.renderer.width = 80
        self.renderer.tokeniser.glyph_offset = self.offset

        result = list(
            self.renderer.split_text_token(
                TextToken(value='Hi', offset=self.offset),
                remainder=self.renderer.width,
            )
        )
        expected = [
            TextToken(value='Hi', offset=self.offset),
        ]
        assert result == expected


class TestGenLines:
    'Test gen_lines method - core line generation logic'

    def setup_method(self) -> None:
        self.renderer = create_renderer('')
        self.offset = 0
        self.renderer.tokeniser.glyph_offset = self.offset

    def test_gen_lines_simple_text(self) -> None:
        self.renderer.tokeniser.data = 'Hello'

        result = list(self.renderer.gen_lines())
        expected = [
            [
                TextToken(value='Hello', offset=self.offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_text_with_newline(self) -> None:
        self.renderer.tokeniser.data = 'Hello\nWorld'

        result = list(self.renderer.gen_lines())
        expected = [
            [
                TextToken(value='Hello', offset=self.offset),
                SGRToken(value='0'),
                NewLineToken(value='\n'),
            ],
            [
                TextToken(value='World', offset=self.offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ],
        ]
        assert result == expected

    def test_gen_lines_text_at_width_boundary(self) -> None:
        self.renderer.tokeniser.data = 'A' * 80

        lines = list(self.renderer.gen_lines())
        expected = [
            [
                TextToken(value='A' * 80, offset=self.offset),
                SGRToken(value='0'),
                NewLineToken(value='\n'),
            ],
        ]
        assert lines == expected

    def test_gen_lines_text_exceeds_width(self) -> None:
        self.renderer.tokeniser.data = 'A' * 100

        tokens = list(self.renderer.tokeniser.tokenise())
        expected_tokens = [
            TextToken(value='A' * 100, offset=self.offset),
        ]
        assert tokens == expected_tokens

        result = list(self.renderer.gen_lines())
        expected = [
            [
                TextToken(value='A' * 80, offset=self.offset),
                SGRToken(value='0'),
                NewLineToken(value='\n'),
            ],
            [
                TextToken(value='A' * 20, offset=self.offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ],
        ]

        assert result == expected

    def test_gen_lines_with_colors(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31mRed\x1b[0m'

        result = list(self.renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                Color8BGToken(value='40'),
                TextToken(value='Red', offset=self.offset),
                SGRToken(value='0'),
                Color8FGToken(value='37'),
                Color8BGToken(value='40'),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_preserves_colors_across_wraps(self) -> None:
        # When text wraps, colors should be preserved on the next line
        data = '\x1b[31m' + 'A' * 90 + '\x1b[0m'
        self.renderer.tokeniser.data = data

        result = list(self.renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                Color8BGToken(value='40'),
                TextToken(value='A' * 80, offset=self.offset),
                SGRToken(value='0'),
                NewLineToken(value='\n'),
            ],
            [
                Color8FGToken(value='31'),
                Color8BGToken(value='40'),
                TextToken(value='A' * 10, offset=self.offset),
                SGRToken(value='0'),
                Color8FGToken(value='37'),
                Color8BGToken(value='40'),
                SGRToken(value='0'),
                EOFToken(value=''),
            ],
        ]
        assert result == expected

    def test_gen_lines_color_reset_clears_state(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31mRed\x1b[0mNormal'

        result = list(self.renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                Color8BGToken(value='40'),
                TextToken(value='Red', offset=self.offset),
                SGRToken(value='0'),
                Color8FGToken(value='37'),
                Color8BGToken(value='40'),
                TextToken(value='Normal', offset=self.offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_multiple_colors(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31mRed\x1b[32mGreen\x1b[34mBlue'

        result = list(self.renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                Color8BGToken(value='40'),
                TextToken(value='Red', offset=self.offset),
                Color8FGToken(value='32'),
                Color8BGToken(value='40'),
                TextToken(value='Green', offset=self.offset),
                Color8FGToken(value='34'),
                Color8BGToken(value='40'),
                TextToken(value='Blue', offset=self.offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_empty_input(self) -> None:
        self.renderer.tokeniser.data = ''

        result = list(self.renderer.gen_lines())
        expected: list = []
        assert result == expected

    def test_gen_lines_control_sequences(self) -> None:
        self.renderer.tokeniser.data = 'Hello\x1b[5CWorld'

        result = list(self.renderer.gen_lines())
        expected = [
            [
                TextToken(value='Hello', offset=self.offset),
                ControlToken(value='\x1b[5C'),
                TextToken(value='World', offset=self.offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_cursor_position_clears_line(self) -> None:
        self.renderer.tokeniser.data = 'Hello\x1b[10;20HWorld'

        result = list(self.renderer.gen_lines())
        expected = [
            [
                TextToken(value='Hello', offset=self.offset),
                ControlToken(value='\x1b[10;20H'),
                TextToken(value='World', offset=self.offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_width_20(self) -> None:
        self.renderer.tokeniser.data = 'HelloWorldThisIsATest'
        self.renderer.width = 20

        result = list(self.renderer.gen_lines())
        expected = [
            [
                TextToken(value='HelloWorldThisIsATes', offset=self.offset),
                SGRToken(value='0'),
                NewLineToken(value='\n'),
            ],
            [
                TextToken(value='t', offset=self.offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ],
        ]
        assert result == expected

    def test_gen_lines_fg_and_bg_colors(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31;44mColoredText\x1b[0m'

        result = list(self.renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                Color8BGToken(value='44'),
                TextToken(value='ColoredText', offset=self.offset),
                SGRToken(value='0'),
                Color8FGToken(value='37'),
                Color8BGToken(value='40'),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_ice_colours(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31;44mText'
        self.renderer.tokeniser.ice_colours = True

        result = list(self.renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                Color8BGToken(value='44'),
                TextToken(value='Text', offset=self.offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected


class TestIterLines:
    'Test iter_lines method - converts token lines to strings'

    def setup_method(self) -> None:
        self.renderer = create_renderer(data='')
        self.offset = 0
        self.renderer.tokeniser.glyph_offset = self.offset

    def test_iter_lines_simple(self) -> None:
        self.renderer.tokeniser.data = 'Hello'

        result = list(self.renderer.iter_lines())
        expected = [
            TextToken._translate_chars('Hello', self.offset) + '\x1b[0m',
        ]

        assert result == expected

    def test_iter_lines_multiple_lines(self) -> None:
        self.renderer.tokeniser.data = 'Hello\nWorld'

        result = list(self.renderer.iter_lines())
        expected = [
            TextToken._translate_chars('Hello', self.offset) + '\x1b[0m\n',
            TextToken._translate_chars('World', self.offset) + '\x1b[0m',
        ]
        assert result == expected

    def test_iter_lines_with_colors(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31mRed\x1b[0m'

        result = list(self.renderer.iter_lines())
        expected = [
            '\x1b[31m\x1b[40m' + TextToken._translate_chars('Red', self.offset) + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m',
        ]
        assert result == expected

    def test_iter_lines_preserves_reset(self) -> None:
        self.renderer.tokeniser.data = 'Test'

        result = list(self.renderer.iter_lines())
        expected = [
            TextToken._translate_chars('Test', self.offset) + '\x1b[0m',
        ]
        assert result == expected


class TestRender:
    'Test render method - combines all lines into final output'

    def setup_method(self) -> None:
        self.renderer = create_renderer(data='')
        self.offset = 0
        self.renderer.tokeniser.glyph_offset = self.offset

    def test_render_simple_text(self) -> None:
        self.renderer.tokeniser.data = 'Hello World'

        result = self.renderer.render()
        expected = TextToken._translate_chars('Hello World', self.offset) + '\x1b[0m'
        assert result == expected

    def test_render_with_newlines(self) -> None:
        self.renderer.tokeniser.data = 'Hello\nWorld'

        result = self.renderer.render()
        expected = (
            TextToken._translate_chars('Hello', self.offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('World', self.offset)
            + '\x1b[0m'
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
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m'
        )
        assert result == expected

    def test_render_long_text_wraps(self) -> None:
        self.renderer.tokeniser.data = 'A' * 100

        result = self.renderer.render()
        expected = (
            TextToken._translate_chars('A' * 80, self.offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('A' * 20, self.offset)
            + '\x1b[0m'
        )
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
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m\n'
            + '\x1b[37m\x1b[40m\x1b[32m\x1b[40m'
            + TextToken._translate_chars('║  ANSI Art Test   ║', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m\n'
            + '\x1b[37m\x1b[40m\x1b[34m\x1b[40m'
            + TextToken._translate_chars('╚══════════════════╝', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m'
        )
        assert result == expected

    def test_render_preserves_color_state(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31m' + 'A' * 90 + '\x1b[0m'

        result = self.renderer.render()
        expected = (
            '\x1b[31m\x1b[40m'
            + TextToken._translate_chars('A' * 80, self.offset)
            + '\x1b[0m\n'
            + '\x1b[31m\x1b[40m'
            + TextToken._translate_chars('A' * 10, self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m'
        )
        assert result == expected

    def test_render_ice_colours_mode(self) -> None:
        self.renderer.tokeniser.data = '\x1b[1;5;31;44mBright Text\x1b[0m'
        self.renderer.tokeniser.ice_colours = True

        result = self.renderer.render()
        expected = (
            '\x1b[1m\x1b[91m\x1b[104m'
            + TextToken._translate_chars('Bright Text', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m'
        )
        assert result == expected

    def test_render_no_trailing_garbage(self) -> None:
        self.renderer.tokeniser.data = 'Clean'

        result = self.renderer.render()
        expected = TextToken._translate_chars('Clean', self.offset) + '\x1b[0m'
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
            + '\x1b[0m'
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
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m'
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
        self.renderer.tokeniser.width = 40

        result = list(self.renderer.iter_lines())
        expected = [
            TextToken._translate_chars(data[:40], self.offset) + '\x1b[0m\n',
            TextToken._translate_chars(data[40:], self.offset) + '\x1b[0m',
        ]
        assert result == expected


class TestRendererEdgeCases:
    'Test edge cases and special scenarios'

    def setup_method(self) -> None:
        self.renderer = create_renderer(data='')
        self.offset = 0
        self.renderer.tokeniser.glyph_offset = self.offset

    def test_single_character(self) -> None:
        self.renderer.tokeniser.data = 'A'

        result = self.renderer.render()
        expected = TextToken._translate_chars('A', self.offset) + '\x1b[0m'
        assert result == expected

    def test_width_1(self) -> None:
        self.renderer.tokeniser.data = 'ABC'
        self.renderer.tokeniser.width = 1
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
        self.renderer.tokeniser.width = 5
        self.renderer.width = 5

        result = self.renderer.render()
        expected = '\n'.join([
            TextToken._translate_chars('X' * 5, self.offset) + '\x1b[0m',
            TextToken._translate_chars('X' * 5, self.offset) + '\x1b[0m',
            TextToken._translate_chars('X' * 5, self.offset) + '\x1b[0m',
            TextToken._translate_chars('X' * 5, self.offset) + '\x1b[0m',
            TextToken._translate_chars('X' * 2, self.offset) + '\x1b[0m',
        ])
        assert result == expected

    def test_consecutive_newlines(self) -> None:
        self.renderer.tokeniser.data = 'A\n\n\nB'

        result = self.renderer.render()
        expected = (
            TextToken._translate_chars('A', self.offset)
            + '\x1b[0m\n'
            + '\x1b[0m\n'
            + '\x1b[0m\n'
            + TextToken._translate_chars('B', self.offset)
            + '\x1b[0m'
        )
        assert result == expected

    def test_color_without_text(self) -> None:
        self.renderer.tokeniser.data = '\x1b[31m\x1b[44m'

        result = self.renderer.render()
        expected = '\x1b[31m\x1b[40m\x1b[31m\x1b[44m\x1b[0m'
        assert result == expected

    def test_mixed_ansi_sequences(self) -> None:
        self.renderer.tokeniser.data = '\x1b[1m\x1b[31m\x1b[44mStyled\x1b[0m'

        result = self.renderer.render()
        expected = (
            '\x1b[1m\x1b[97m\x1b[40m\x1b[31m\x1b[40m\x1b[31m\x1b[44m'
            + TextToken._translate_chars('Styled', self.offset)
            + '\x1b[0m\x1b[37m\x1b[40m\x1b[0m'
        )
        assert result == expected
