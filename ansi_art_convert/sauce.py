from __future__ import annotations

import os
from itertools import batched
from typing import Any, NamedTuple, Tuple

from ansi_art_convert.encoding import SupportedEncoding
from ansi_art_convert.font_data import FILE_DATA_TYPES, FONT_DATA
from ansi_art_convert.log import dprint

ASPECT_RATIO_MAP = {
    (0, 0): 'Legacy value. No preference.',
    (
        0,
        1,
    ): 'Image was created for a legacy device. When displayed on a device with square pixels, either the font or the image needs to be stretched.',
    (
        1,
        0,
    ): 'Image was created for a modern device with square pixels. No stretching is desired on a device with square pixels.',
    (1, 1): 'Not currently a valid value.',
}
LETTER_SPACING_MAP = {
    (0, 0): 'Legacy value. No preference.',
    (0, 1): 'Select 8 pixel font.',
    (1, 0): 'Select 9 pixel font.',
    (1, 1): 'Not currently a valid value.',
}
TINFO_NAMES = ['tinfo1', 'tinfo2', 'tinfo3', 'tinfo4']


class SauceRecordExtended(NamedTuple):
    'extended sauce record with extra fields for interpreted/expanded comments, font & flag descriptions'

    fpath: str
    encoding: SupportedEncoding
    sauce: SauceRecord
    comments_data: list[str]
    font: dict
    tinfo: dict
    aspect_ratio: str
    letter_spacing: str
    non_blink_mode: bool
    ice_colours: bool

    @staticmethod
    def write_comments(comments_data: list[str]) -> str:
        if not comments_data:
            return ''
        return 'COMNT' + ''.join(c.ljust(64, '\x00') for c in comments_data)

    @staticmethod
    def parse_comments(comment_block: str, n_comments: int) -> list[str]:
        if len(comment_block) != (n_comments * 64) + 5:
            raise ValueError(f'Invalid comment block size: expected {n_comments * 64 + 5}, got {len(comment_block)}')

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
            'aspect_ratio': ASPECT_RATIO_MAP.get((ar1, ar2), 'Unknown'),
            'letter_spacing': LETTER_SPACING_MAP.get((ls1, ls2), 'Unknown'),
            'non_blink_mode': bool(b),
        }

    @staticmethod
    def parse_font(font_name: str) -> dict:
        return FONT_DATA.get(font_name, {})

    @staticmethod
    def parse_tinfo_field(tinfo_key: str, sauce: SauceRecord) -> dict:
        if sauce.data_type == 5:
            # ('BinaryText', 'Variable'): {'tinfo1': '0', 'tinfo2': '0', 'tinfo3': '0', 'tinfo4': '0' }``
            raise NotImplementedError('SAUCE tinfo parsing for data_type 5 (BinaryText) is not implemented.')
        return {
            'name': FILE_DATA_TYPES.get((sauce.data_type, sauce.file_type), {}).get(tinfo_key, '0'),
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
    def parse(
        sauce: SauceRecord, file_data: str, fpath: str, encoding: SupportedEncoding
    ) -> Tuple[SauceRecordExtended, str]:
        flags = SauceRecordExtended.parse_flags(sauce.flags)
        font = SauceRecordExtended.parse_font(sauce.tinfo_s.strip())
        tinfo = SauceRecordExtended.parse_tinfo(sauce)
        ice_colours = flags.get('non_blink_mode', False)

        kwargs = {
            'fpath': fpath,
            'encoding': encoding,
            'sauce': sauce,
            'comments_data': [],
            **flags,
            'font': font,
            'tinfo': tinfo,
            'ice_colours': ice_colours,
        }
        if sauce.comments == 0:
            return SauceRecordExtended(**kwargs), file_data

        blockIdx = len(file_data) - (sauce.comments * 64 + 5)
        data, comment_block = file_data[:blockIdx], file_data[blockIdx:]

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
                'file_name': os.path.basename(self.fpath),
                'encoding': self.encoding.value,
                'comments': self.comments_data,
                'tinfo': self.tinfo,
                'aspect_ratio': self.aspect_ratio,
                'letter_spacing': self.letter_spacing,
                'non_blink_mode': self.non_blink_mode,
                'font': self.font,
                'ice_colours': self.ice_colours,
            },
        }


class SauceRecord(NamedTuple):
    ID: str = ''  #   5b
    version: str = ''  # + 2b  = 7b
    title: str = ''  # + 35b = 42b
    author: str = ''  # + 20b = 62b
    group: str = ''  # + 20b = 82b
    date: str = ''  # + 8b  = 90b
    filesize: int = 0  # + 4b  = 94b
    data_type: int = 0  # + 1b  = 95b
    file_type: int = 0  # + 1b  = 96b
    tinfo1: int = 0  # + 2b  = 98b
    tinfo2: int = 0  # + 2b  = 100b
    tinfo3: int = 0  # + 2b  = 102b
    tinfo4: int = 0  # + 2b  = 104b
    comments: int = 0  # + 1b  = 105b
    flags: int = 0  # + 1b  = 106b
    tinfo_s: str = ''  # + 22b = 128b

    @staticmethod
    def offsets() -> dict[str, Tuple[int, int]]:
        return {
            'ID': (0, 5),
            'version': (5, 7),
            'title': (7, 42),
            'author': (42, 62),
            'group': (62, 82),
            'date': (82, 90),
            'filesize': (90, 94),
            'data_type': (94, 95),
            'file_type': (95, 96),
            'tinfo1': (96, 98),
            'tinfo2': (98, 100),
            'tinfo3': (100, 102),
            'tinfo4': (102, 104),
            'comments': (104, 105),
            'flags': (105, 106),
            'tinfo_s': (106, 128),
        }

    def is_empty(self) -> bool:
        return self.ID != 'SAUCE'

    @staticmethod
    def parse_field(key: str, raw_value: bytes, encoding: str) -> str | int:
        if key in {
            'data_type',
            'file_type',
            'comments',
            'filesize',
            'tinfo1',
            'tinfo2',
            'tinfo3',
            'tinfo4',
            'flags',
        }:
            return int.from_bytes(raw_value.rstrip(b'\x00'), byteorder='little', signed=False)
        else:
            return raw_value.replace(b'\x00', b'').strip().decode(encoding)

    @staticmethod
    def parse_record(file_data: bytes, encoding: str) -> Tuple[SauceRecord, str]:
        data, sauce_data = file_data[:-128], file_data[-128:]

        if not (sauce_data and sauce_data.startswith(b'SAUCE')):
            return SauceRecord(), file_data.decode(encoding)

        values: dict[str, Any] = {}
        for key, (start, end) in SauceRecord.offsets().items():
            values[key] = SauceRecord.parse_field(key, sauce_data[start:end], encoding)

        return SauceRecord(**values), data.decode(encoding)

    def record_bytes(self, encoding: str) -> bytes:
        record_bytes = bytearray(128)
        for key, (start, end) in SauceRecord.offsets().items():
            value = getattr(self, key)
            if isinstance(value, int):
                value_bytes = value.to_bytes(end - start, byteorder='little', signed=False)
            else:
                value_bytes = value.encode(encoding)[: end - start].ljust(end - start, b'\x00')
            record_bytes[start:end] = value_bytes
        return bytes(record_bytes)
