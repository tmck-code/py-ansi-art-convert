# SAUCE Metadata

- [SAUCE Metadata](#sauce-metadata)
  - [Field Definitions](#field-definitions)
    - [FileType \& DataType](#filetype--datatype)
    - [TInfo \& Flag Fields](#tinfo--flag-fields)
    - [Notes](#notes)
  - [ANSiFlags](#ansiflags)
    - [AR: Aspect Ratio](#ar-aspect-ratio)
    - [LS: Letter-spacing (a.k.a. 8/9 pixel font selection).](#ls-letter-spacing-aka-89-pixel-font-selection)
    - [B: Non-blink mode (iCE Color).](#b-non-blink-mode-ice-color)
  - [FontName Field Values](#fontname-field-values)

---

## Field Definitions

### FileType & DataType

| DataType  | Name       | FileType | Name   | Description                                                    |
|-----------|------------|----------|--------|----------------------------------------------------------------|
| 1         | Character  | 0        | ASCII  | Plain ASCII text file with no formatting codes or color codes. |
| 1         | Character  | 1        | ANSi   | A file with ANSi coloring codes and cursor positioning.        |

### TInfo & Flag Fields

| Name  | TInfo1 [1]          | TInfo2 [1]          | TInfo3 [1]  | TInfo4 [1] | Flags [1] | TInfoS [2] |
|-------|---------------------|---------------------|-------------|------------|-----------|------------|
| ASCII | Character width [3] | Number of lines [4] | 0           | 0          | ANSiFlags | FontName   |
| ANSi  | Character width [3] | Number of lines [4] | 0           | 0          | ANSiFlags | FontName   |

### Notes

1. A 0 here means the value should always be set to zero, otherwise it can optionally contain the matching value.
2. A 0 here means the field should be set to all binary zeroes, otherwise it can optionally contain a a set of flags.
3. The width in characters the screen or window should be set to in order to properly display the file. A value of 0 means no width was provided and you should use an appropriate default (usually 80).
4. Either 0 or the number of lines the file occupies when fully rendered. Some ANSI files have incorrect values for this, having the screen height instead. You could use the value as a guide for preallocating a rendering buffer. Do not assume the value is correct, the actual number of screen lines could be lower or higher.

---

## ANSiFlags
ANSiFlags allow an author of ANSi and similar files to provide a clue to a viewer / editor how to render the image.   
The 8 bits in the ANSiFlags contain the following information:

```
|           |  AR   |  LS   | B |
| 0 | 0 | 0 | A | R | L | S | B |
```

These bits are interpreted as:

### AR: Aspect Ratio
Most modern display devices have square pixels, but that has not always been the case. Displaying an ANSI file that was created for one of the older devices on a device with square pixels will vertically compress the image slightly. This can be compensated for by either taking a font that is slightly taller than was used on the legacy device, or by stretching the rendered image.

These 2 bits can be used to signal that the image was created with square pixels in mind, or that it was created for a legacy device with the elongated pixels:

- 00: Legacy value. No preference.
- 01: Image was created for a legacy device. When displayed on a device with square pixels, either the font or the image needs to be stretched.
- 10: Image was created for a modern device with square pixels. No stretching is desired on a device with square pixels.
- 11: Not currently a valid value.

### LS: Letter-spacing (a.k.a. 8/9 pixel font selection).

Fixed-width text mode as used in DOS and early graphics based computers such as the Amiga used bitmap fonts to display text. Letter-spacing and line spacing is a part of the font bitmap, so the font box inside each bitmap was a bit smaller than the font bitmap.   

For the VGA, IBM wanted a smoother font. 2 more lines were added, and the letter-spacing was removed from the font and instead inserted by the VGA hardware during display.   

All 8 pixels in the font could thus be used, and still have a 1 pixel letter spacing. For the line graphics characters, this was a problem because they needed to match up with their neighbours on both sides. The VGA hardware was wired to duplicate the 8th column of the font bitmap for the character range C0h to DFh. In some code pages was undesired, so this feature could be turned off to get an empty letter spacing on all characters as well (via the ELG field (Enable Line Graphics Character Codes) in the Mode Control register (10h) of the VGA Attribute Controller (3C0h). While the VGA allows you to enable or disable the 8th column duplication, there is no way to specify which range of characters this needs to be done for, the C0h to DFh range is hardwired into the VGA.   

These 2 bits can be used to select the 8 pixel or 9 pixel variant of a particular font:   
- 00: Legacy value. No preference.
- 01: Select 8 pixel font.
- 10: Select 9 pixel font.
- 11: Not currently a valid value.

Changing the font width and wanting to remain at 80 characters per row means that you need to adjust for a change in horizontal resolution (from 720 pixels to 640 or vice versa). When you are trying to match the original aspect ratio (see the AR bits), you will need to adjust the vertical stretching accordingly.
Only the VGA (and the Hercules) video cards actually supported fonts 9 pixels wide. SAUCE does not prevent you from specifying you want a 9 pixel wide font for a font that technically was never used that way. Note that duplicating the 8th column on non-IBM fonts (and even some code pages for IBM fonts) may not give the desired effect.
Some people like the 9 pixel fonts, some do not because it causes a visible break in the 3 ‘shadow blocks’ (B0h, B1h and B2h)

### B: Non-blink mode (iCE Color).
When 0, only the 8 low intensity colors are supported for the character background. The high bit set to 1 in each attribute byte results in the foreground color blinking repeatedly.
When 1, all 16 colors are supported for the character background. The high bit set to 1 in each attribute byte selects the high intensity color instead of blinking.

---

## FontName Field Values

| Font name [1]          | Font size | Resolution [1] | A:R[3][4] | Pixel A:R [3][5] | V Stretch [6] | Description                                                                                                                                                                                                                         |
|------------------------|-----------|----------------|-----------|------------------|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| IBM VGA                | 9×16 [7]  | 720×400        | 4:3       | 20:27 (1:1.35)   | 35%           | Standard hardware font on VGA cards for 80×25 text mode (code page 437)                                                                                                                                                             |
|                        | 8×16      | 640×400        | 4:3       | 6:5 (1:1.2)      | 20%           | Modified stats when using an 8 pixel wide version of "IBM VGA" or code page variant.                                                                                                                                                |
| IBM VGA50              | 9×8 [7]   | 720×400        | 4:3       | 20:27 (1:1.35)   | 35%           | Standard hardware font on VGA cards for condensed 80×50 text mode (code page 437)                                                                                                                                                   |
|                        | 8×8       | 640×400        | 4:3       | 5:6 (1:1.2)      | 20%           | Modified stats when using an 8 pixel wide version of "IBM VGA50" or code page variant.                                                                                                                                              |
| IBM VGA25G             | 8×19      | 640×480        | 4:3       | 1:1              | 0%            | Custom font for emulating 80×25 in VGA graphics mode 12 (640×480 16 color) (code page 437).                                                                                                                                         |
| IBM EGA                | 8×14      | 640×350        | 4:3       | 35:48 (1:1.3714) | 37.14%        | Standard hardware font on EGA cards for 80×25 text mode (code page 437)                                                                                                                                                             |
| IBM EGA43              | 8×8       | 640×350        | 4:3       | 35:48 (1:1.3714) | 37.14%        | Standard hardware font on EGA cards for condensed 80×43 text mode (code page 437)                                                                                                                                                   |
| IBM VGA ### [8]        | 9×16 [7]  | 720×400        | 4:3       | 20:27 (1:1.35)   | 35%           | Software installed code page font for VGA 80×25 text mode                                                                                                                                                                           |
| IBM VGA50 ### [8]      | 9×8 [7]   | 720×400        | 4:3       | 20:27 (1:1.35)   | 35%           | Software installed code page font for VGA condensed 80×50 text mode                                                                                                                                                                 |
| IBM VGA25G ### [8]     | 8×19      | 640×480        | 4:3       | 1:1              | 0%            | Custom font for emulating 80×25 in VGA graphics mode 12 (640×480 16 color).                                                                                                                                                         |
| IBM EGA ### [8]        | 8×14      | 640×350        | 4:3       | 35:48 (1:1.3714) | 37.14%        | Software installed code page font for EGA 80×25 text mode                                                                                                                                                                           |
| IBM EGA43 ### [8]      | 8×8       | 640×350        | 4:3       | 35:48 (1:1.3714) | 37.14%        | Software installed code page font for EGA condensed 80×43 text mode                                                                                                                                                                 |
| Amiga Topaz 1          | 8×8 [9]   | 640×200        | 4:3       | 5:12 (1:2.4)     | 140%          | Original Amiga Topaz Kickstart 1.x font. (A500, A1000, A2000)                                                                                                                                                                       |
| Amiga Topaz 1+         | 8×8 [9]   | 640×200        | 4:3       | 5:12 (1:2.4)     | 140%          | Modified Amiga Topaz Kickstart 1.x font. (A500, A1000, A2000)                                                                                                                                                                       |
| Amiga Topaz 2          | 8×8 [9]   | 640×200        | 4:3       | 5:12 (1:2.4)     | 140%          | Original Amiga Topaz Kickstart 2.x font (A600, A1200, A4000)                                                                                                                                                                        |
| Amiga Topaz 2+         | 8×8 [9]   | 640×200        | 4:3       | 5:12 (1:2.4)     | 140%          | Modified Amiga Topaz Kickstart 2.x font (A600, A1200, A4000)                                                                                                                                                                        |
| Amiga P0T-NOoDLE       | 8×8 [9]   | 640×200        | 4:3       | 5:12 (1:2.4)     | 140%          | Original P0T-NOoDLE font.                                                                                                                                                                                                           |
| Amiga MicroKnight      | 8×8 [9]   | 640×200        | 4:3       | 5:12 (1:2.4)     | 140%          | Original MicroKnight font.                                                                                                                                                                                                          |
| Amiga MicroKnight+     | 8×8 [9]   | 640×200        | 4:3       | 5:12 (1:2.4)     | 140%          | Modified MicroKnight font.                                                                                                                                                                                                          |
| Amiga mOsOul           | 8×8 [9]   | 640×200        | 4:3       | 5:12 (1:2.4)     | 140%          | Original mOsOul font.                                                                                                                                                                                                               |
| C64 PETSCII unshifted  | 8×8 [10]  | 320×200        | 4:3       | 5:6 (1:1.2)      | 20%           | Original Commodore PETSCII font (PET, VIC-20, C64, CBM-II, Plus/4, C16, C116 and C128) in the unshifted mode. Unshifted mode (graphics) only has uppercase letters and additional graphic characters. This is the normal boot font. |
| C64 PETSCII shifted    | 8×8 [10]  | 320×200        | 4:3       | 5:6 (1:1.2)      | 20%           | Original PETSCII font in shifted mode. Shifted mode (text) has both uppercase and lowercase letters. This mode is actuated by pressing Shift+Commodore key.                                                                         |
| Atari ATASCII          | 8×8 [11]  | 320×192        | 4:3       | 4:5 (1:1.25)     | 25%           | Original ATASCII font (Atari 400, 800, XL, XE)                                                                                                                                                                                      |

<details>
<summary>Notes</summary>

1. The font name the author designed the artwork for. Since these are typically bitmapped fonts that only support 256 characters, these fonts have a fixed size and are designed with a specific use in mind. Characters in the range 32-127 tend to follow the ASCII encoding which is now also the basis of the same range in Unicode. Control characters in the range 0 to 31 are typically not displayable in text mode formats like ANSI files and require more direct access to the hardware to get them displayed. The visual appearance of these control characters is not part of the ASCII standard. Characters in the range 128-255 are different for each font. For the IBM PC, IBM designed their own encoding which later became known as code page 437. Some other systems (Amiga, C64, ...) used their own encoding for the high characters that did not follow the IBM code page convention. If you do not support a particular font in this list, either fallback to an appropriate less specific definition of the same font, or fallback to whatever default font your program supports.
   As a simple but effective fallback strategy for the IBM family of fonts:
   - If you do not support the VGA25G, VGA50 or EGA43 variant of a font, fallback to the VGA or EGA variant. (string-replace "VGA50" and "VGA25G" with "VGA" and "EGA43" with "EGA")
   - If you do not support EGA fonts, fallback to the matching VGA variant and vice versa. (string-replace "EGA" with "VGA" or vice versa).
   - Code page `872` and `855` are mostly interchangeable (only different for the euro sign).
   - Code page `858` and `850` are mostly interchangeable (only different for the euro sign).
   - Code page `865` and `437` are mostly interchangeable (9Bh '' replacing '' and 9Dh '' replacing '').
   - If you do not support the specific code page, fallback to default variant. (remove " ###" from the end of the string)
   - Fallback to whatever font your program uses as default.
   For the Amiga family of fonts:
   - If you do not support the "+" version of a font, fallback to the normal version. (remove the "+" from the string)
   - If you do not support the custom font, fallback to Amiga Topaz 1
   - Fallback to whatever font your program uses as default.
2. The screen resolution the font was intended for.
3. The aspect ratio is the ratio of the width of a shape to its height. The aspect ratio is expressed as two numbers separated by a colon (width:height). These values do not express an actual measurement, they represent the relation between width and height. If the width is larger than the height the shape has a "landscape" orientation. Width equal to height gives a square. Width smaller than height gives a "portrait" orientation.
4. The aspect ratio of the display device the font was intended for. Up until around 2003 the common display device was either a CRT computer monitor or a CRT TV which usually had a display aspect ratio of 4:3, and occasionally 5:4. Those formats are being replaced by "widescreen" displays commonly having a 16:10 or 16:9 aspect ratio.
5. Modern display devices (LCD, LED and plasma) tend to have square pixels or at least as near square as is technically feasible, because square pixels make it easy to draw squares and circles. For various technical reasons square pixels have not always been the norm however.   
   The downside of this is that if one tries to display an image or font on a display with a different aspect ratio than it was intended for, the image will appear to be stretched or compressed. All the old display modes tended to have a pixels that were taler than they were wide, so they will appear compressed vertically on a display with a 1:1 pixel aspect ratio.   
   You can compensate for this compression by stretching the image, but this will introduce pixelation when you just duplicate pixel lines or blurring when you apply anti-aliassing or interpolation.   
   Similar to trying to display a 4:3 TV signal on a widescreen display, some people will prefer the compressed but 'native pixel' sharpness, and others will prefer the native dimension and accept the loss in sharpness.   
   The pixel aspect ratio is obtained by dividing the display aspect ratio width by the horizontal resolution and dividing the display aspect ratio height by the vertical resolution and then reducing both sides of the ratio.   
6. The stretching percentage that needs to be applied to the composed bitmap so that its relative size matches the original device it was intended for. The actual calculation for this stretch percentage would normally involve knowing the current display aspect ratio as well as the resolution. However since most modern screens have a 1:1 aspect ratio, this can simplified to:   
   ((pixel aspect ratio height / pixel aspect ratio width) - 1) * 100   
   Or alternatively:   
   ```
   (
      (
         (display aspect height / y-resolution)
         / (display aspect width / x-resolution)
      ) -1
   ) * 100
   ```
7. 9 pixel fonts. to be completed
8. The "###" is a placeholder, these 3 characters should be replaced by one of the code pages IBM/Microsoft defined for use in DOS. The possible values for code page *###* are:
   - `437`: The character set of the original IBM PC. Also known as 'MS-DOS Latin US'.
   - `720`: Arabic. Also known as 'Windows-1256'.
   - `737`: Greek. Also known as 'MS-DOS Greek'.
   - `775`: Baltic Rim (Estonian, Lithuanian and Latvian). Also known as 'MS-DOS Baltic Rim'.
   - `819`: Latin-1 Supplemental. Also known as 'Windows-28591' and 'ISO/IEC 8859-1'. It is commonly mistaken for 'Windows-1252' which it resembles except for the 80h-9fh range (C1 control codes).
   - `850`: Western Europe. Also known as 'MS-DOS Latin 1'. Designed to include all the language glyphs, part of the line graphics characters were sacrificed, which made some DOS programs appear strange. Because of this most systems in these countries stuck with CP437 instead.
   - `852`: Central Europe (Bosnian, Croatian, Czech, Hungarian, Polish, Romanian, Serbian and Slovak). Also known as 'MS-DOS Latin 2'. Designed to include all the language glyphs, part of the line graphics characters were sacrificed, which made some DOS programs appear strange. Because of this, several countries adopted their own unofficial encoding system instead.
   - `855`: Cyrillic (Serbian, Macedonian Bulgarian, Russian). Also known as 'MS-DOS Cyrillic'. Used in Serbia, Macedonia and Bulgaria, but eventually replaced by CP866. Never caught on in Russia.
   - `857`: Turkish. Also known as 'MS-DOS Turkish'. Based on CP850 and designed to include all characters from ISO 8859-9 (with a different encoding).
   - `858`: Western Europe. Identical to CP850 but has the euro sign at D5h instead. Also known as 'Modified code page 850'.
   - `860`: Portuguese. Also known as 'MS-DOS Portuguese'. Even though this code page preserves all the line graphics characters, Brazil has mainly adopted CP850 which does not.
   - `861`: Icelandic. Also known as 'MS-DOS Icelandic'.
   - `862`: Hebrew. Also known as 'MS-DOS Hebrew'. Obsolete on modern operating systems, replaced by Unicode which preserves the logical bidirectional order (which DOS could not).
   - `863`: French Canada. Also known as 'MS-DOS French Canada'.
   - `864`: Arabic. Sacrifices all of the line graphics characters (encoding the single line box characters differently) in order to get more Arabic symbols. CP720 does preserve the line graphics characters.
   - `865`: Nordic.
   - `866`: Cyrillic.
   - `869`: Greek 2. Also known as 'MS-DOS Greek 2'. Designed to include all the glyphs from ISO 8859-7 (with a different encoding), part of the line graphics characters were sacrificed, which made some DOS programs appear strange. This made CP869 unpopular and most Greek systems used CP737 instead.
   - `872`: Cyrillic. Identical to CP855 but has the euro sign at CFh instead.
   - `KAM`: 'Kamenick' encoding. Also known as 'KEYBCS2'. Used for Czech, this code page was custom designed as an alternative for CP852 to preserved the line graphics characters while providing the characters needed for the Czech language. Supported in some DOS clones under the unofficial code page number 867 or 895.
   - `MAZ`: 'Mazovia' encoding. Used for Polish, this code page was custom designed as an alternative for CP852 to preserved the line graphics characters while providing the characters needed for the Polish language. Supported in some DOS clones under the unofficial code page number 667 or 790.
   - `MIK`: Cyrillic. Most widespread codepage in Bulgaria. Supported in some DOS clones under the unofficial code page number 866.
   So for example "IBM VGA 855" would select the VGA 9×16 font for code page 855 for 80×25 text mode.   
   Unsupported code pages:
   - `667`: Unofficial code page number for 'Mazovia' encoding, use "MAZ" instead.
   - `790`: Unofficial code page number for 'Mazovia' encoding on FreeDOS, use "MAZ" instead.
   - `866`: Unofficial code page number for 'MIK' encoding, use "MIK" instead.
   - `867`: Unofficial code page number for 'Kamenick' encoding, use "KAM" instead.
   - `895`: Unofficial code page number for 'Kamenick' encoding, use "KAM" instead.
   - `991`: Unofficial code page number, depending on the Operating System or device its meaning could differ. Probably refers to "MAZ".
9. The Amiga 500 typically works at a 640×200 resolution or 640×400 in interlaced mode on NTSC monitor (USA and Japan), and at 640×256 (640×512 interlaced) on PAL monitors (most of Europe). In interlaced mode, rather than condensing the font to achieve double the amount of lines of text, the font instead was stretched to double its size.
   It is not uncommon to now find programs using a pre-stretched 8×16 font for displaying Amiga ANSI files. In that case, the pixel ratio mentioned here should be adjusted accordingly to 5:6 (1:1.2) and the vertical stretching to 20%
10. This font was used in a 40×25 character mode. It may be necessary to double the size of the font or image to get the "chunky" look.
11. This font was used in a 40×24 character mode. It may be necessary to double the size of the font or image to get the "chunky" look.

</details>
