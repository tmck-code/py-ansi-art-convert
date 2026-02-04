#!/usr/bin/env python3

import glob
import os
import shutil
import sys
import time
from itertools import batched

from tqdm import tqdm

def screenshot():
    os.makedirs('screenshots', exist_ok=True)
    os.system(f'flameshot screen -p ./screenshots 2> /dev/null')

def crop(ifpath, ofpath, x, y, w, h):
    os.system(f'magick {ifpath} -crop {w}x{h}+{x}+{y} tmp.png && mv tmp.png {ofpath}')

def vertical_stack(images, ofpath):
    inputs = ' '.join(images)
    os.system(f'magick {inputs} -append {ofpath}')

def get_mtimes(root, files):
    for f in files:
        yield os.path.getmtime(root+f), f

import operator as op
def sort_by_mtime(file_list: list[str]) -> list[str]:
    for _mtime, f in sorted(get_mtimes('', file_list)):
        yield f

data = open(sys.argv[1]).readlines()
output_png = sys.argv[2]
window_height = shutil.get_terminal_size().lines

print(f'printing {len(data[:window_height])} initial lines and {len(data[window_height:])} remainder lines')

time.sleep(2)

initial, remainder = data[:window_height], data[window_height:]

for line in initial:
    print(' ', line, flush=True, end='')

screenshot()

for lines in batched(remainder, window_height-1):
    for line in lines:
        print(' ', line, flush=True, end='')
    screenshot()

fpaths = list(sort_by_mtime(glob.glob('./screenshots/*.png')))

with tqdm(total=len(fpaths)) as pbar:
    for fpath in fpaths:
        crop(fpath, fpath, 20, 78, 972, 1274)
        pbar.update()

vertical_stack(fpaths, output_png)
