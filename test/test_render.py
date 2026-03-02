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
    Tokeniser,
)
from ansi_art_convert.encoding import SupportedEncoding
from ansi_art_convert.sauce import SauceRecord, SauceRecordExtended


def create_mock_sauce(width: int = 80, ice_colours: bool = False, font_name: str = 'IBM VGA') -> SauceRecordExtended:
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


def create_tokeniser(
    data: str, width: int = 80, ice_colours: bool = False, encoding: SupportedEncoding = SupportedEncoding.UTF_8
) -> Tokeniser:
    return Tokeniser(
        fpath='/test/file.ans',
        sauce=create_mock_sauce(width=width, ice_colours=ice_colours),
        data=data,
        font_name='Amiga mOsOul',
        encoding=encoding,
        width=width,
        ice_colours=ice_colours,
    )


def create_renderer(data: str, width: int = 80, ice_colours: bool = False) -> Renderer:
    return Renderer(
        fpath='/test/file.ans',
        tokeniser=create_tokeniser(data, width=width, ice_colours=ice_colours),
    )


class TestRendererInit:
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


class TestRendererSplitTextToken:
    'Test split_text_token method for line wrapping'

    def setup_class(self) -> None:
        self.renderer = Renderer(
            fpath='/test/file.ans',
            tokeniser=create_tokeniser(''),
        )

    def test_split_text_token_exact_fit(self) -> None:
        self.renderer.width = 5
        # Test splitting text that's exactly 15 chars with 5 char remainder
        result = list(
            self.renderer.split_text_token(
                TextToken(value='HelloWorldAbcde', offset=self.renderer.tokeniser.glyph_offset),
                remainder=5,
            )
        )
        s = ''.join(chr(ord(el) + self.renderer.tokeniser.glyph_offset) for el in 'HelloWorldAbcde')
        expected = [
            TextToken(value=s[:5], offset=self.renderer.tokeniser.glyph_offset),
            TextToken(value=s[5:10], offset=self.renderer.tokeniser.glyph_offset),
            TextToken(value=s[10:], offset=self.renderer.tokeniser.glyph_offset),
        ]
        assert result == expected

    def test_split_text_token_multiple_chunks(self) -> None:
        self.renderer.width = 5

        result = list(
            self.renderer.split_text_token(
                TextToken(value='A' * 25, offset=self.renderer.tokeniser.glyph_offset),
                remainder=self.renderer.width,
            )
        )
        expected = [
            TextToken(value='A' * 5, offset=self.renderer.tokeniser.glyph_offset),
        ] * 5
        assert result == expected

    def test_split_text_token_no_split_needed(self) -> None:
        self.renderer.width = 80

        result = list(
            self.renderer.split_text_token(
                TextToken(value='Hi', offset=self.renderer.tokeniser.glyph_offset),
                remainder=self.renderer.width,
            )
        )
        expected = [
            TextToken(value='Hi', offset=self.renderer.tokeniser.glyph_offset),
        ]
        assert result == expected


class TestRendererGenLines:
    'Test gen_lines method - core line generation logic'

    def setup_class(self) -> None:
        self.renderer = create_renderer('')

    def test_gen_lines_simple_text(self) -> None:
        renderer = create_renderer(data='Hello')

        result = list(renderer.gen_lines())
        expected = [
            [
                TextToken(value='Hello', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_text_with_newline(self) -> None:
        renderer = create_renderer(data='Hello\nWorld')

        result = list(renderer.gen_lines())
        expected = [
            [
                TextToken(value='Hello', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                NewLineToken(value='\n'),
            ],
            [
                TextToken(value='World', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ],
        ]
        assert result == expected

    def test_gen_lines_text_at_width_boundary(self) -> None:
        renderer = create_renderer(data='A' * 80, width=80)

        lines = list(renderer.gen_lines())
        expected = [
            [
                TextToken(value='A' * 80, offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                NewLineToken(value='\n'),
            ],
        ]
        assert lines == expected

    def test_gen_lines_text_exceeds_width(self) -> None:
        renderer = create_renderer(data='A' * 100, width=80)

        tokens = list(renderer.tokeniser.tokenise())
        expected_tokens = [
            TextToken(value='A' * 100, offset=renderer.tokeniser.glyph_offset),
        ]
        assert tokens == expected_tokens

        result = list(renderer.gen_lines())
        expected = [
            [
                TextToken(value='A' * 80, offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                NewLineToken(value='\n'),
            ],
            [
                TextToken(value='A' * 20, offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ],
        ]

        assert result == expected

    def test_gen_lines_with_colors(self) -> None:
        renderer = create_renderer(data='\x1b[31mRed\x1b[0m')

        result = list(renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                TextToken(value='Red', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_preserves_colors_across_wraps(self) -> None:
        # When text wraps, colors should be preserved on the next line
        data = '\x1b[31m' + 'A' * 90 + '\x1b[0m'
        renderer = create_renderer(data=data, width=80)

        result = list(renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                TextToken(value='A' * 80, offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                NewLineToken(value='\n'),
            ],
            [
                Color8FGToken(value='31'),
                TextToken(value='A' * 10, offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ],
        ]
        assert result == expected

    def test_gen_lines_color_reset_clears_state(self) -> None:
        renderer = create_renderer(data='\x1b[31mRed\x1b[0mNormal')

        result = list(renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                TextToken(value='Red', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                TextToken(value='Normal', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_multiple_colors(self) -> None:
        renderer = create_renderer(data='\x1b[31mRed\x1b[32mGreen\x1b[34mBlue')

        result = list(renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                TextToken(value='Red', offset=renderer.tokeniser.glyph_offset),
                Color8FGToken(value='32'),
                TextToken(value='Green', offset=renderer.tokeniser.glyph_offset),
                Color8FGToken(value='34'),
                TextToken(value='Blue', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_empty_input(self) -> None:
        renderer = create_renderer(data='')

        result = list(renderer.gen_lines())
        expected: list = []
        assert result == expected

    def test_gen_lines_control_sequences(self) -> None:
        renderer = create_renderer(data='Hello\x1b[5CWorld', width=80)

        result = list(renderer.gen_lines())
        expected = [
            [
                TextToken(value='Hello', offset=renderer.tokeniser.glyph_offset),
                ControlToken(value='\x1b[5C'),
                TextToken(value='World', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_cursor_position_clears_line(self) -> None:
        renderer = create_renderer(data='Hello\x1b[10;20HWorld', width=80)

        result = list(renderer.gen_lines())
        expected = [
            [
                TextToken(value='Hello', offset=renderer.tokeniser.glyph_offset),
                ControlToken(value='\x1b[10;20H'),
                TextToken(value='World', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_width_20(self) -> None:
        renderer = create_renderer(data='HelloWorldThisIsATest', width=20)

        result = list(renderer.gen_lines())
        expected = [
            [
                TextToken(value='HelloWorldThisIsA', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                NewLineToken(value='\n'),
            ],
            [
                TextToken(value='Test', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ],
        ]
        assert result == expected

    def test_gen_lines_fg_and_bg_colors(self) -> None:
        renderer = create_renderer(data='\x1b[31;44mColoredText\x1b[0m')

        result = list(renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                Color8BGToken(value='44'),
                TextToken(value='ColoredText', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected

    def test_gen_lines_ice_colours(self) -> None:
        renderer = create_renderer(data='\x1b[31;44mText', ice_colours=True)

        result = list(renderer.gen_lines())
        expected = [
            [
                Color8FGToken(value='31'),
                Color8BGToken(value='44'),
                TextToken(value='Text', offset=renderer.tokeniser.glyph_offset),
                SGRToken(value='0'),
                EOFToken(value=''),
            ]
        ]
        assert result == expected


class TestRendererIterLines:
    'Test iter_lines method - converts token lines to strings'

    def test_iter_lines_simple(self) -> None:
        renderer = create_renderer(data='Hello')

        result = list(renderer.iter_lines())
        expected = [
            TextToken._translate_chars('Hello', renderer.tokeniser.glyph_offset) + '\x1b[0m',
        ]

        assert result == expected

    def test_iter_lines_multiple_lines(self) -> None:
        renderer = create_renderer(data='Hello\nWorld')

        result = list(renderer.iter_lines())
        expected = [
            TextToken._translate_chars('Hello', renderer.tokeniser.glyph_offset) + '\x1b[0m\n',
            TextToken._translate_chars('World', renderer.tokeniser.glyph_offset) + '\x1b[0m',
        ]
        assert result == expected

    def test_iter_lines_with_colors(self) -> None:
        renderer = create_renderer(data='\x1b[31mRed\x1b[0m')

        result = list(renderer.iter_lines())
        expected = [
            '\x1b[31m' + TextToken._translate_chars('Red', renderer.tokeniser.glyph_offset) + '\x1b[0m',
        ]
        assert result == expected

    def test_iter_lines_preserves_reset(self) -> None:
        renderer = create_renderer(data='Test')

        result = list(renderer.iter_lines())
        expected = [
            TextToken._translate_chars('Test', renderer.tokeniser.glyph_offset) + '\x1b[0m',
        ]
        assert result == expected


class TestRendererRender:
    'Test render method - combines all lines into final output'

    def test_render_simple_text(self) -> None:
        renderer = create_renderer(data='Hello World')

        result = renderer.render()
        expected = TextToken._translate_chars('Hello World', renderer.tokeniser.glyph_offset) + '\x1b[0m'
        assert result == expected

    def test_render_with_newlines(self) -> None:
        renderer = create_renderer(data='Hello\nWorld')

        result = renderer.render()
        expected = (
            TextToken._translate_chars('Hello', renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('World', renderer.tokeniser.glyph_offset)
            + '\x1b[0m'
        )
        assert result == expected

    def test_render_with_colors(self) -> None:
        renderer = create_renderer(data='\x1b[31mRed\x1b[32mGreen\x1b[0m')

        result = renderer.render()
        expected = (
            '\x1b[31m'
            + TextToken._translate_chars('Red', renderer.tokeniser.glyph_offset)
            + '\x1b[32m'
            + TextToken._translate_chars('Green', renderer.tokeniser.glyph_offset)
            + '\x1b[0m'
        )
        assert result == expected

    def test_render_long_text_wraps(self) -> None:
        renderer = create_renderer(data='A' * 100, width=80)

        result = renderer.render()
        expected = (
            TextToken._translate_chars('A' * 80, renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('A' * 20, renderer.tokeniser.glyph_offset)
            + '\x1b[0m'
        )
        assert result == expected

    def test_render_empty_input(self) -> None:
        renderer = create_renderer(data='')

        result = renderer.render()
        expected = ''
        assert result == expected

    def test_render_complex_ansi_art(self) -> None:
        # Test with complex ANSI art-like content
        data = (
            '\x1b[31m╔══════════════════╗\x1b[0m\n'
            '\x1b[32m║  ANSI Art Test   ║\x1b[0m\n'
            '\x1b[34m╚══════════════════╝\x1b[0m'
        )
        renderer = create_renderer(data=data, width=80)

        result = renderer.render()
        expected = (
            '\x1b[31m'
            + TextToken._translate_chars('╔══════════════════╗', renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
            + '\x1b[32m'
            + TextToken._translate_chars('║  ANSI Art Test   ║', renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
            + '\x1b[34m'
            + TextToken._translate_chars('╚══════════════════╝', renderer.tokeniser.glyph_offset)
            + '\x1b[0m'
        )
        assert result == expected

    def test_render_preserves_color_state(self) -> None:
        renderer = create_renderer(data='\x1b[31m' + 'A' * 90 + '\x1b[0m', width=80)

        result = renderer.render()
        expected = (
            '\x1b[31m'
            + TextToken._translate_chars('A' * 80, renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
            + '\x1b[31m'
            + TextToken._translate_chars('A' * 10, renderer.tokeniser.glyph_offset)
            + '\x1b[0m'
        )
        assert result == expected

    def test_render_ice_colours_mode(self) -> None:
        renderer = create_renderer(data='\x1b[1;5;31;44mBright Text\x1b[0m', ice_colours=True)

        result = renderer.render()
        expected = (
            '\x1b[1m\x1b[5m\x1b[31m\x1b[44m'
            + TextToken._translate_chars('Bright Text', renderer.tokeniser.glyph_offset)
            + '\x1b[0m'
        )
        assert result == expected

    def test_render_no_trailing_garbage(self) -> None:
        renderer = create_renderer(data='Clean')

        result = renderer.render()
        expected = TextToken._translate_chars('Clean', renderer.tokeniser.glyph_offset) + '\x1b[0m'
        assert result == expected

    def test_render_handles_control_sequences(self) -> None:
        renderer = create_renderer(data='Start\x1b[10CMiddle\x1b[5CEnd', width=80)

        result = renderer.render()
        expected = (
            TextToken._translate_chars('Start', renderer.tokeniser.glyph_offset)
            + ' ' * 10
            + TextToken._translate_chars('Middle', renderer.tokeniser.glyph_offset)
            + ' ' * 5
            + TextToken._translate_chars('End', renderer.tokeniser.glyph_offset)
            + '\x1b[0m'
        )
        assert result == expected

    def test_render_multiple_resets(self) -> None:
        renderer = create_renderer(data='\x1b[31mRed\x1b[0m\x1b[32mGreen\x1b[0m\x1b[34mBlue\x1b[0m')

        result = renderer.render()
        expected = (
            '\x1b[31m'
            + TextToken._translate_chars('Red', renderer.tokeniser.glyph_offset)
            + '\x1b[0m\x1b[32m'
            + TextToken._translate_chars('Green', renderer.tokeniser.glyph_offset)
            + '\x1b[0m\x1b[34m'
            + TextToken._translate_chars('Blue', renderer.tokeniser.glyph_offset)
            + '\x1b[0m'
        )
        assert result == expected

    def test_render_exact_width_boundary(self) -> None:
        renderer = create_renderer(data='X' * 80 + 'Y' * 80, width=80)

        result = renderer.render()
        expected = (
            TextToken._translate_chars('X' * 80, renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('Y' * 80, renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
        )
        assert result == expected

    def test_render_width_40(self) -> None:
        data = 'The quick brown fox jumps over the lazy dog'

        renderer = create_renderer(data=data, width=40)
        renderer.tokeniser.glyph_offset = 0

        result = list(renderer.iter_lines())
        expected = [
            TextToken._translate_chars(data[:40], renderer.tokeniser.glyph_offset) + '\x1b[0m\n',
            TextToken._translate_chars(data[40:], renderer.tokeniser.glyph_offset) + '\x1b[0m',
        ]
        assert result == expected


class TestRendererEdgeCases:
    'Test edge cases and special scenarios'

    def test_single_character(self) -> None:
        renderer = create_renderer(data='A')

        result = renderer.render()
        expected = TextToken._translate_chars('A', renderer.tokeniser.glyph_offset) + '\x1b[0m'
        assert result == expected

    def test_width_1(self) -> None:
        renderer = create_renderer(data='ABC', width=1)

        result = renderer.render()
        expected = (
            TextToken._translate_chars('A', renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('B', renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
            + TextToken._translate_chars('C', renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
        )
        assert result == expected

    def test_very_long_line(self) -> None:
        renderer = create_renderer(data='X' * 1000, width=80)

        result = renderer.render().count('\n')
        expected = 13  # 1000 / 80 = 12.5, so 13 lines (12 full + 1 partial)
        assert result == expected

    def test_consecutive_newlines(self) -> None:
        renderer = create_renderer(data='A\n\n\nB')

        result = renderer.render()
        expected = (
            TextToken._translate_chars('A', renderer.tokeniser.glyph_offset)
            + '\x1b[0m\n'
            + '\x1b[0m\n'
            + '\x1b[0m\n'
            + TextToken._translate_chars('B', renderer.tokeniser.glyph_offset)
            + '\x1b[0m'
        )
        assert result == expected

    def test_color_without_text(self) -> None:
        renderer = create_renderer(data='\x1b[31m\x1b[44m')

        result = renderer.render()
        expected = '\x1b[31m\x1b[44m'
        assert result == expected

    def test_mixed_ansi_sequences(self) -> None:
        renderer = create_renderer(data='\x1b[1m\x1b[31m\x1b[44mStyled\x1b[0m')

        result = renderer.render()
        expected = (
            '\x1b[1m\x1b[31m\x1b[44m'
            + TextToken._translate_chars('Styled', renderer.tokeniser.glyph_offset)
            + '\x1b[0m'
        )
        assert result == expected
