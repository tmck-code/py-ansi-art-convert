#!/usr/bin/env python3

from argparse import ArgumentParser
from typing import TextIO

from ansi_art_convert import convert

args = {'fpath': 'tmp/28-SUSHI.ANS'}


def run(ifpath: str, ostream: TextIO) -> None:
    print(f'Parsing {ifpath}...')
    encoding, sauce_extended, data = convert.parse_info({'fpath': ifpath})
    t = convert.Tokeniser(**(args | {'encoding': encoding, 'sauce': sauce_extended, 'data': data}))
    r = convert.Renderer(fpath=args['fpath'], tokeniser=t)

    print(f'encoding={encoding}, len(data)={len(data)}')

    convert.set_glyph_offset(0)

    print(f'{encoding=}, {sauce_extended=}, {len(data)=}')

    line: list[convert.ANSIToken] = []
    for tok in t.tokenise():
        if isinstance(tok, convert.Color8Token):
            continue
        elif isinstance(tok, convert.NewLineToken):
            print('[', file=ostream)
            for el in line:
                print(f'    {el!r},', file=ostream)
            print(']', file=ostream)
            line.clear()
        else:
            line.append(tok)


def parse_args() -> dict:
    parser = ArgumentParser(description='Debug an ANSi file by printing the tokens')
    parser.add_argument('fpath', help='The path to the ANSi file to debug')
    parser.add_argument('--output', '-o', help='The path to the output file (default: <input>.debug.ANS)')
    return parser.parse_args().__dict__


def main():
    args = parse_args()
    print(f'args={args}')
    with open(args['output'], 'w') as ostream:
        run(args['fpath'], ostream)


if __name__ == '__main__':
    main()
