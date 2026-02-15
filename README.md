# ANSI Art Converter

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/tmck-code/py-ansi-art-convert/test.yml)
![PyPI - Version](https://img.shields.io/pypi/v/ansi-art-convert)

A tool to convert original ANSI art files for viewing in a modern terminal.   

- [Installation](#installation)
- [Usage](#usage)
- [Documentation](#documentation)
- [Resources](#resources)

> [!IMPORTANT]
> _This is **not** an AI-generated project. I wrote this myself, and I test it extensively against original artwork._

---

## Installation

You can install the [`ansi-art-convert`](https://pypi.org/project/ansi-art-convert/) package via pip:

```shell
pip install ansi-art-convert
```

> [!IMPORTANT]
> _As a prerequisite, you will need to install the [`ANSI megafont`](https://github.com/tmck-code/ansi-megafont) on your system via your regular font installer, and ensure that your terminal emulator is configured to use it._

Alternatively, you can install it via a one-liner (you will still need to configure your terminal to use it):
<details>
<summary>install commands:</summary>

```shell
# osx
curl -sOL --output-dir ~/Library/Fonts/ https://github.com/tmck-code/ansi-megafont/releases/download/v0.1.1/ANSICombined.ttf \
  && fc-cache -f ~/Library/Fonts/ \
  && fc-list | grep "ANSICombined"

# linux
curl -sOL --output-dir ~/.fonts/ https://github.com/tmck-code/ansi-megafont/releases/download/v0.1.1/ANSICombined.ttf \
  && fc-cache -f ~/.fonts/ \
  && fc-list | grep "ANSICombined"
```

</details>

## Usage

```shell
usage: ansi-art-convert [-h] --fpath FPATH [--encoding ENCODING] [--sauce-only] [--verbose] [--ice-colours] [--font-name FONT_NAME] [--width WIDTH]

options:
  -h, --help            show this help message and exit
  --fpath, -f FPATH     Path to the ANSI file to render.
  --encoding, -e ENCODING
                        Specify the file encoding (cp437, iso-8859-1, ascii, utf-8) if the auto-detection was incorrect.
  --sauce-only, -s      Only output the SAUCE record information as JSON and exit.
  --verbose, -v         Enable verbose debug output.
  --ice-colours         Force enabling ICE colours (non-blinking background).
  --font-name FONT_NAME
                        Specify the font name to determine glyph offset (overrides SAUCE font).
  --width, -w WIDTH     Specify the output width (overrides SAUCE tinfo1).
```

## Documentation

- [SAUCE Metadata](docs/sauce.md)

## Resources

- [The origins of DEL (0x7F) and its Legacy in Amiga ASCII art](https://blog.glyphdrawing.club/the-origins-of-del-0x7f-and-its-legacy-in-amiga-ascii-art/)
- [rewtnull/amigafonts](https://github.com/rewtnull/amigafonts)
- [Screwtapello/topaz-unicode](https://gitlab.com/Screwtapello/topaz-unicode)
- [Rob Hagemans' Hoard of Bitfonts](https://github.com/robhagemans/hoard-of-bitfonts)
- [amigavision/TopazDouble](https://github.com/amigavision/TopazDouble)
