#!/usr/bin/env python3

from collections import Counter
import glob
import operator as op
import os
import re
import shutil
import subprocess
import sys
import time
from itertools import batched
from typing import Type

from PIL import Image
import numpy as np
from tqdm import tqdm
from wcwidth import wcswidth

from i3_client import main as i3

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

def timestamp():
    return int(time.time() * 10**6)

class OSUtils:
    @staticmethod
    def screenshot():
        raise NotImplementedError()

class OSX(OSUtils):
    @staticmethod
    def _get_screen_dimensions() -> list[int]:
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
        raise RuntimeError('Could not get screen dimensions')

    @staticmethod
    def _get_capture_rectangle() -> tuple[int, int, int, int]:
        'returns x, y, w, h'
        screen_w, screen_h = OSX._get_screen_dimensions()
        return (0, 90, screen_w, screen_h-1260)

    @staticmethod
    def screenshot():
        x, y, w, h = OSX._get_capture_rectangle()
        rectangle = f"{x},{y},{w},{h}"
        os.system(f"screencapture -R {rectangle} ./screenshots/{timestamp()}.png 2> /dev/null")
        # print(f"screencapture -l {get_window_id()} -R {rectangle} ./screenshots/{timestamp()}.png 2> /dev/null")
        print(f"screencapture -R {rectangle} ./screenshots/{timestamp()}.png 2> /dev/null")

class Linux(OSUtils):
    @staticmethod
    def _get_capture_rectangle() -> tuple[int, int, int, int]:
        'returns x, y, w, h'
        geom = i3.find_focused_node(i3.get_i3_tree()).rect
        return geom.x+2, geom.y+55, geom.width-50, geom.height-120

    @staticmethod
    def screenshot():
        x, y, w, h = Linux._get_capture_rectangle()
        os.system(f'flameshot screen --region {w}x{h}+{x}+{y} -p ./screenshots/{timestamp()} 2> /dev/null')

def get_os_utils() -> Type[OSUtils]:
    if sys.platform == 'darwin':
        return OSX
    elif sys.platform.startswith('linux'):
        return Linux
    else:
        raise RuntimeError(f'Unsupported platform: {sys.platform}')

def get_border_coords(img: Image.Image, border_colour: tuple[int, int, int]) -> tuple[int, int, int, int]:
    'Returns (x1, y1, x2, y2) coordinates of the border in the image.'
    # Convert to numpy array for vectorized operations
    pixels = np.array(img)
    rgb = pixels[:, :, :3]

    # Create mask for border color pixels
    border_mask = np.all(rgb == border_colour, axis=2)
    # Exclude first row and column (to match range(1, ...))
    border_mask[0, :], border_mask[:, 0] = False, False

    # Get coordinates and find gaps
    y_coords, x_coords = np.where(border_mask)

    # Find gaps in x coordinates - need to look at sorted by frequency
    x_counts = Counter(x_coords)
    x_sorted_by_freq = [k for k, v in x_counts.most_common()]
    for i in range(1, len(x_sorted_by_freq)):
        if x_sorted_by_freq[i] != x_sorted_by_freq[i-1] + 1:
            x1 = x_sorted_by_freq[i-1]
            x2 = x_sorted_by_freq[i]
            break

    # Find gaps in y coordinates - need to look at sorted by frequency  
    y_counts = Counter(y_coords)
    y_sorted_by_freq = [k for k, v in y_counts.most_common()]
    for i in range(1, len(y_sorted_by_freq)):
        if y_sorted_by_freq[i] != y_sorted_by_freq[i-1] + 1:
            y1 = y_sorted_by_freq[i-1]
            y2 = y_sorted_by_freq[i]
            break

    return x1+1, y1+1, x2, y2

def crop_border(img: Image.Image, border_colour: tuple[int, int, int]) -> Image.Image:
    x1, y1, x2, y2 = get_border_coords(img, border_colour)
    return img.crop((x1, y1, x2, y2))

def crop(ifpath, ofpath):
    img = Image.open(ifpath).convert('RGBA')
    border_colour = (170, 170, 170)
    cropped_img = crop_border(img, border_colour)
    cropped_img.save(ofpath)

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
    data = open(fpath).readlines()

    t_size = shutil.get_terminal_size()
    window_height, window_width = t_size.lines, t_size.columns

    print(
        f'printing {len(data[:window_height])} initial lines '
        f'and {len(data[window_height:])} remainder lines'
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
    # input()

    for lines in batched(remainder, window_height):
        print(__white_fg(' ')*(window_width), flush=True)
        for line in lines:
            line_remainder = line_width - get_visible_width(line.strip())
            padding = ' ' * (window_width - get_visible_width(line.strip())-line_remainder-1)
            print(__white_fg(' ')+line.strip()+' '*line_remainder+__white_fg(padding), flush=True)
        for _ in range(window_height-len(lines)+1):
            print(__white_fg(' ')*(window_width), flush=True)
        yield # screenshot here
        # input()

def sort_by_mtime(file_list: list[str]) -> list[str]:
    for _mtime, f in sorted(get_mtimes("", file_list)):
        yield f

def main(text_file, line_width, output_png):
    os.makedirs("screenshots", exist_ok=True)
    os_utils = get_os_utils()
    print(f'Using OS utils: {os_utils.__name__}')

    # 1. take all the screenshots
    for chunk in scroll_file(text_file, line_width):
        os_utils.screenshot()

    # clear the terminal - it's pretty harsh/bright to look at due to the white border
    print('\033c', end='')

    # 2. crop all the screenshots
    fpaths = list(sort_by_mtime(glob.glob("./screenshots/*.png")))
    with tqdm(total=len(fpaths)) as pbar:
        for fpath in fpaths:
            crop(fpath, fpath)
            pbar.update()

    # 3. Create single vertical PNG
    vertical_stack(fpaths, output_png)

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])