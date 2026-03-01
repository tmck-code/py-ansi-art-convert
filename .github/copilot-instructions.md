# ANSI Art Converter - AI Coding Agent Instructions

## Project Overview
This is a Python CLI tool that converts legacy ANSI/ASCII art files for modern terminal viewing by:
1. Parsing SAUCE metadata (Standard Architecture for Universal Comment Extensions)
2. Tokenizing ANSI escape sequences and legacy character encodings
3. Mapping legacy font glyphs to Unicode Private Use Area (PUA) codepoints (0xE000+)
4. Rendering with proper line wrapping and color handling

**Critical**: This is NOT an AI-generated project. The author hand-crafted this with extensive testing against original artwork. Maintain this quality standard.

## Architecture: Token-Based Pipeline

### Core Flow: File → SAUCE → Tokeniser → Renderer → Output
1. **[sauce.py](../ansi_art_convert/sauce.py)**: Parse 128-byte SAUCE record from file end, extract metadata (encoding, font, width, ICE colors flag)
2. **[encoding.py](../ansi_art_convert/encoding.py)**: Auto-detect encoding by counting CP437 box-drawing chars vs ISO-8859-1 patterns
3. **[convert.py](../ansi_art_convert/convert.py)**: `Tokeniser.tokenise()` creates token stream; `Renderer.gen_lines()` handles line wrapping
4. **[font_data.py](../ansi_art_convert/font_data.py)**: `FONT_OFFSETS` map font names → PUA base offset (e.g., `'IBM VGA': 0xE800`)

### Token Hierarchy (18 types)
```python
ANSIToken (base)
├── TextToken       # Regular text, applies glyph_offset in __post_init__
│   ├── C0Token     # Control chars (0x00-0x1F), strips CR
│   └── CP437Token  # Uses UNICODE_TO_CP437 mapping for extended chars
├── ControlToken    # ESC[...A/B/C/D/H/J/K (cursor/erase), __str__ converts to spaces/newlines
├── ColorFGToken / ColorBGToken
│   ├── TrueColorFGToken / TrueColorBGToken  # ESC[38;2;R;G;Bm / ESC[48;2;R;G;Bm
│   ├── Color256FGToken / Color256BGToken    # ESC[38;5;Nm / ESC[48;5;Nm
│   └── Color8FGToken / Color8BGToken        # ESC[30-37m / ESC[40-47m, handles ICE colors
├── Color8Token     # Composite parser for SGR sequences, calls generate_tokens()
├── SGRToken        # Text attributes (bold/dim/italic/underline/blink/reset)
├── NewLineToken / EOFToken / UnknownToken
```

**Key Pattern**: Token `__str__()` methods emit terminal codes; `repr()` methods provide debug output (only used if `--verbose`).

## Critical Implementation Details

### Glyph Offset System
Legacy fonts (Amiga Topaz, IBM VGA) use custom glyphs for chars 0x00-0xFF. Map to PUA to avoid Unicode conflicts:
```python
# TextToken.__post_init__ transforms each byte:
if ord(v) <= 255:
    new_values.append(chr(ord(v) + self.offset))  # offset from FONT_OFFSETS dict
```
**Amiga fonts**: 0xE000-0xE700 range; **IBM VGA**: 0xE800. See [font_data.py L211-235](../ansi_art_convert/font_data.py).

### ICE Colors (Non-Blink Mode)
When SAUCE flag bit 0 is set or `--ice-colours` passed:
- Background color high bit (normally blink) selects bright backgrounds (colors 100-107 vs 40-47)
- Detected in SAUCE parsing: `non_blink_mode = bool(flags & 0x01)`
- Applied in Color8Token: `Color8BGToken(value='40', ice_colours=True)` → outputs `\x1b[100m`

### Line Wrapping (Renderer)
SAUCE `tinfo1` field specifies width (default 80). Renderer breaks lines:
```python
def gen_lines(self):  # Generator yields token lists per line
    for token in self.tokeniser.tokens:
        if isinstance(token, TextToken):
            for chunk in self.split_text_token(token.value, remainder, TextToken):
                # Track remainder, emit NewLineToken when remainder hits 0
```
**Edge case**: CursorForward control codes (`ESC[nC`) convert to spaces in line length calc.

### SAUCE Parsing Quirks
- Comment block starts at `len(file_data) - (n_comments * 64 + 5)` and must begin with `COMNT` (5 bytes)
- Font name in `tinfo_s` field (22 bytes, null-terminated) maps to FONT_DATA dict
- If no font specified, CP437 files default to `'IBM VGA'` ([convert.py L485](../ansi_art_convert/convert.py))

## Development Workflow

### Running Tests
```bash
. .venv/bin/activate  # Activate virtual environment
python3 -m pytest test/           # All tests, ~50 test cases
python3 -m pytest test/test_tokens.py::TestCP437Token  # Single test class
```

### CLI Usage Patterns
```bash
ansi-art-convert -f file.ans              # Auto-detect encoding
ansi-art-convert -f file.ans -e cp437     # Force encoding
ansi-art-convert -f file.ans -s           # SAUCE metadata only (JSON output)
ansi-art-convert -f file.ans -v           # Debug output (dprint logs)
ansi-art-convert -f file.ans --ice-colours --width 40  # Override SAUCE
```

### Code Style
- Single quotes for strings (ruff enforced)
- Type hints mandatory (`disallow_untyped_defs = true`)
- Dataclasses for all tokens (use `field(default_factory=...)` for mutable defaults)
- Debug prints via `dprint()` from [log.py](../ansi_art_convert/log.py), gated by global `DEBUG` flag

## Common Gotchas

1. **Token immutability**: Store `original_value` in `__post_init__` before transforming `value`
2. **SAUCE comment indexing**: Off-by-one errors common; comment block size = `64 * n_comments + 5`
3. **Encoding detection false positives**: Files with few box chars can misdetect as ISO-8859-1
4. **Test data isolation**: Use `create_mock_sauce()` helper ([test_render.py L27](../test/test_render.py)), never read real files in unit tests
5. **CP437 special chars**: `UNICODE_TO_CP437` dict is sparse (only non-identity mappings), check for key existence

## Extending the Project

### Adding a new token type:
1. Subclass `ANSIToken` in [convert.py](../ansi_art_convert/convert.py)
2. Implement `__str__()` (emit terminal code) and `repr()` (debug view)
3. Add detection logic in `Tokeniser.create_tokens()` (parses `\x1b[...` sequences)
4. Add test class in [test/test_tokens.py](../test/test_tokens.py) with `test_*_init`, `test_*_str`, `test_*_repr` methods

### Adding a new font:
1. Add entry to `FONT_DATA` dict in [font_data.py](../ansi_art_convert/font_data.py) with metadata
2. Assign PUA offset in `FONT_OFFSETS` (increment by 0x100 from last Amiga font)
3. Create `.ttf` in [ansi-megafont](https://github.com/tmck-code/ansi-megafont) repo at matching PUA offset
4. Add alias to `FONT_ALIASES` for CLI convenience

## Key Files Reference
- **[convert.py](../ansi_art_convert/convert.py)** (732 lines): Token classes, Tokeniser, Renderer, CLI entrypoint
- **[sauce.py](../ansi_art_convert/sauce.py)** (213 lines): SAUCE metadata parsing, flags interpretation
- **[font_data.py](../ansi_art_convert/font_data.py)** (488 lines): Font metadata, PUA offsets, CP437 mapping
- **[encoding.py](../ansi_art_convert/encoding.py)** (124 lines): Auto-detection heuristics
- **[test/](../test/)**: 3 test files (test_tokens.py, test_tokenise.py, test_render.py), ~500 lines total
