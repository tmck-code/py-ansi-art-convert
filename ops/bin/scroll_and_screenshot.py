#!/usr/bin/env python3

import glob
import operator as op
import os
import shutil
import subprocess
import sys
import time
from itertools import batched

from tqdm import tqdm

import re
from wcwidth import wcswidth

def get_screen_dimensions() -> list[int, int]:
    s = subprocess.run(
        ['system_profiler', 'SPDisplaysDataType'],
        capture_output=True
    ).stdout.decode().strip().split('\n')

    for i, el in enumerate(s):
        dims = []
        if 'Resolution' in el:
            for j in el.split(' '):
                if j.isnumeric():
                    dims.append(int(j))
            return dims

def get_capture_rectangle() -> tuple[int, int, int, int]:
    'returns x, y, w, h'
    screen_w, screen_h = get_screen_dimensions()
    return (0, 90, screen_w, screen_h-1260)

def get_visible_width(text):
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    visible_text = ansi_escape.sub('', text)
    # Calculate width, handling wide characters
    return wcswidth(visible_text)

def get_tmux_window_index():
    return subprocess.run(
        ["tmux", "display-message", "-p", "#I"],
        capture_output=True
    ).stdout.decode().strip()

def get_window_id():
    return subprocess.run(
        ["GetWindowID", "Alacritty", f"terminal {get_tmux_window_index()}"],
        capture_output=True
    ).stdout.decode().strip()

def timestamp():
    return int(time.time() * 10**6)

def screenshot():
    x, y, w, h = get_capture_rectangle()
    rectangle = f"{x},{y},{w},{h}"
    os.system(f"screencapture -R {rectangle} ./screenshots/{timestamp()}.png 2> /dev/null")
    # print(f"screencapture -l {get_window_id()} -R {rectangle} ./screenshots/{timestamp()}.png 2> /dev/null")
    print(f"screencapture -R {rectangle} ./screenshots/{timestamp()}.png 2> /dev/null")

# magick screenshots/1770191147080937.png -fill none -fuzz 5% -draw "color 0,0 floodfill" -draw "color %[fx:w-1],0 floodfill" -draw "color 0,%[fx:h-1] floodfill" -draw "color %[fx:w-1],%[fx:h-1] floodfill" -alpha off -trim +repage output.png

def crop(ifpath, ofpath, x, y, w, h):
    os.system(
        f"magick '{ifpath}' -crop {w}x{h}+{x}+{y} tmp.png" # && mv tmp.png '{ofpath}'"
    )


def vertical_stack(images, ofpath):
    inputs = " ".join(f"'{i}'" for i in images)
    os.system(f"magick {inputs} -append {ofpath}")


def get_mtimes(root, files):
    for f in files:
        yield os.path.getmtime(root + f), f

WHITE_FG='\x1b[37;47m'
RESET='\x1b[0m'

def __white_fg(text) -> str:
    return f'{WHITE_FG}{text}{RESET}'

def scroll_file(fpath, line_width):
    data = open(sys.argv[1]).readlines()

    t_size = shutil.get_terminal_size()
    window_height, window_width = t_size.lines, t_size.columns

    print(
        f'printing {len(data[:window_height])} initial lines '
        'and {len(data[window_height:])} remainder lines'
    )
    # account for white border above & below the content,
    # and the cursor takes up a line as well
    padding_top, padding_bottom, cursor_line = 1, 1, 1
    y_padding = sum((padding_top, padding_bottom, cursor_line))
    window_height -= y_padding

    initial, remainder = data[:window_height], data[window_height:]

    print(__white_fg(' ')*(window_width), flush=True)
    for i, line in enumerate(initial):
        line_remainder = line_width - get_visible_width(line.strip())
        padding = ' ' * (window_width - get_visible_width(line.strip())-line_remainder-1)
        print(__white_fg(' ')+line.strip()+' '*line_remainder+__white_fg(padding), flush=True)
    print(__white_fg(' ')*(window_width), flush=True)
    yield # screenshot here
    input()

    for lines in batched(remainder, window_height):
        print(__white_fg(' ')*(window_width), flush=True)
        for line in lines:
            line_remainder = line_width - get_visible_width(line.strip())
            padding = ' ' * (window_width - get_visible_width(line.strip())-line_remainder-1)
            print(__white_fg(' ')+line.strip()+' '*line_remainder+__white_fg(padding), flush=True)
        for _ in range(window_height-len(lines)+1):
            print(__white_fg(' ')*(window_width), flush=True)
        yield # screenshot here
        input()

def sort_by_mtime(file_list: list[str]) -> list[str]:
    for _mtime, f in sorted(get_mtimes("", file_list)):
        yield f

def main(text_file, line_width, output_png):
    os.makedirs("screenshots", exist_ok=True)

    # 1. take all the screenshots
    for chunk in scroll_file(text_file, line_width):
        screenshot()

    # 2. crop all the screenshots
    fpaths = list(sort_by_mtime(glob.glob("./screenshots/*.png")))
    # with tqdm(total=len(fpaths)) as pbar:
    #     for fpath in fpaths:
    #         crop(fpath, fpath, 5, 160, 1440, 1950)
    #         pbar.update()

    # 3. Create single vertical PNG
    # vertical_stack(fpaths, output_png)

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])