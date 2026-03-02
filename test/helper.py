from typing import Any

from ansi_art_convert.convert import Renderer, Tokeniser
from ansi_art_convert.encoding import SupportedEncoding
from ansi_art_convert.sauce import SauceRecord, SauceRecordExtended

DEFAULT_WIDTH = 80
DEFAULT_FONT_NAME = 'IBM VGA'
DEFAULT_ENCODING = SupportedEncoding.UTF_8

DEFAULT_SAUCE_RECORD_KWARGS = {
    'ID': 'SAUCE',
    'version': '00',
    'title': 'Test',
    'author': 'Author',
    'group': 'Group',
    'date': '20240101',
    'filesize': 0,
    'data_type': 1,
    'file_type': 1,
    'tinfo1': DEFAULT_WIDTH,
    'tinfo2': 0,
    'tinfo3': 0,
    'tinfo4': 0,
    'comments': 0,
    'flags': 0,
    'tinfo_s': DEFAULT_FONT_NAME,
}

DEFAULT_EXTENDED_KWARGS = {
    'fpath': '/test/file.ans',
    'encoding': DEFAULT_ENCODING,
    'comments_data': [],
    'font': {'name': DEFAULT_FONT_NAME},
    'tinfo': {},
    'aspect_ratio': '',
    'letter_spacing': '',
    'non_blink_mode': False,
    'ice_colours': False,
}


def create_mock_sauce(sauce_record_kwargs: dict[str, Any], extended_kwargs: dict[str, Any]) -> SauceRecordExtended:
    return SauceRecordExtended(
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
            tinfo1=sauce_record_kwargs.get('width', DEFAULT_WIDTH),
            tinfo2=0,
            tinfo3=0,
            tinfo4=0,
            comments=0,
            flags=0 if not extended_kwargs.get('ice_colours', False) else 1,
            tinfo_s=sauce_record_kwargs.get('font_name', DEFAULT_FONT_NAME),
            **{k: v for k, v in sauce_record_kwargs.items() if k not in {'tinfo_s', 'flags'}},
        ),
        fpath='/test/file.ans',
        encoding=SupportedEncoding.CP437,
        comments_data=[],
        font={'name': sauce_record_kwargs.get('font_name', DEFAULT_FONT_NAME)},
        tinfo={},
        aspect_ratio='',
        letter_spacing='',
        non_blink_mode=extended_kwargs.get('ice_colours', False),
        ice_colours=extended_kwargs.get('ice_colours', False),
        **extended_kwargs,
    )


DEFAULT_TOKENISER_KWARGS: dict[str, Any] = {
    'font_name': DEFAULT_FONT_NAME,
    'encoding': DEFAULT_ENCODING,
    'width': DEFAULT_WIDTH,
    'ice_colours': False,
    'fpath': '/test/file.ans',
}


def create_tokeniser(
    data: str = '',
    tokeniser_kwargs: dict[str, Any] = {},
    sauce_record_kwargs: dict[str, Any] = {},
    extended_kwargs: dict[str, Any] = {},
) -> Tokeniser:
    return Tokeniser(
        sauce=create_mock_sauce(sauce_record_kwargs=sauce_record_kwargs, extended_kwargs=extended_kwargs),
        data=data,
        **(DEFAULT_TOKENISER_KWARGS | tokeniser_kwargs),
    )


DEFAULT_RENDERER_KWARGS: dict[str, Any] = {
    'fpath': '/test/file.ans',
}


def create_renderer(
    data: str,
    tokeniser_kwargs: dict[str, Any] = {},
    renderer_kwargs: dict[str, Any] = {},
    sauce_record_kwargs: dict[str, Any] = {},
    extended_kwargs: dict[str, Any] = {},
) -> Renderer:
    return Renderer(
        tokeniser=create_tokeniser(
            data,
            tokeniser_kwargs=tokeniser_kwargs,
            sauce_record_kwargs=sauce_record_kwargs,
            extended_kwargs=extended_kwargs,
        ),
        **(DEFAULT_RENDERER_KWARGS | renderer_kwargs),
    )
