from __future__ import annotations
from enum import Enum
from collections import Counter

from laser_prynter import pp

from ansi_art_convert.log import dprint, DEBUG

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

CP437_SHADE_BLOCK_MAP = (
    0xB0, # '░'
    0xB1, # '▒'
    0xB2, # '█'
)
CP437_BLOCK_MAP = (
    0xDB, # '█'
    0xDC, # '▄'
    0xDD, # '▐'
    0xDE, # '▌'
    0xDF, # '▀'
)
CP437_BOX_MAP = (
    0xC0, # '└'
    0xD9, # '┘'
    0xC3, # '├'
    0xC2, # '┬'
    0xC1, # '┐'
    0xB4, # '┤'
)
CP437_DOUBLE_BOX_MAP = (
    0xB6, #╢
    0xB7, #╖
    0xB8, #╕
    0xB9, #╣
    0xBA, #║
    0xBB, #╗
    0xBC, #╝
    0xBD, #╜
    0xBE, #╛
    0xC6, #╞
    0xC7, #╟
    0xC8, #╚
    0xC9, #╔
    0xCA, #╩
    0xCB, #╦
    0xCC, #╠
    0xCD, #═
    0xCE, #╬
    0xCF, #╧
    0xD0, #╨
    0xD1, #╤
    0xD2, #╥
    0xD3, #╙
    0xD6, #╓
    0xD7, #╫
    0xD8, #╪
)
ISO_8859_1_BOX_MAP = (
    0x7c, # '|'
    0x5c, # '\\'
    0x2f, # '/'
    0xaf, # '¯'
    0x5f, # '_'
)
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

def detect_encoding(data: bytes) -> SupportedEncoding:
    'Detect file encoding based on presence of CP437 block characters.'
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
    for byte in ISO_8859_1_BOX_MAP:
        iso_box_counts[byte] = data.count(byte)

    cp437_shade_counts, cp437_box_counts, cp437_block_counts = Counter(), Counter(), Counter()

    all_counts = (
        (CP437_SHADE_BLOCK_MAP, cp437_shade_counts),
        (CP437_BOX_MAP,         cp437_box_counts),
        (CP437_BLOCK_MAP,       cp437_block_counts),
        (CP437_DOUBLE_BOX_MAP,  cp437_block_counts)
    )

    for bytes, counts in all_counts:
        for byte in bytes:
            count = data.count(byte)
            if count > 0:
                counts[byte] = count

    for c in (cp437_shade_counts, cp437_box_counts, cp437_block_counts):
        if c.total() > 0:
            if DEBUG:
                dprint(f'> [CP437 +1] Detected CP437 characters in file: {c}')
            points[SupportedEncoding.CP437] += 1

    cp437_all_counts = cp437_shade_counts | cp437_box_counts | cp437_block_counts
    if len(cp437_all_counts) > 1:
        if cp437_all_counts.total() < iso_box_counts.total():
            if DEBUG:
                dprint(f'> [ISO +1] Detected more ISO-8859-1 box characters in file than CP437: {iso_box_counts.total()} vs {cp437_all_counts.total()}')
            points[SupportedEncoding.ISO_8859_1] += 1
        else:
            if DEBUG:
                dprint(f'> [CP437 +1] Detected CP437 characters in file: {cp437_all_counts}')
            points[SupportedEncoding.CP437] += 1

    if DEBUG:
        pp.ppd({'points': {k.name: v for k,v in points.items()}}, indent=2)
    return points.most_common(1)[0][0]