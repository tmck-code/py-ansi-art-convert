#!/usr/bin/env python3

import shutil
import sys
import time

data = open(sys.argv[1]).readlines()
window_height = shutil.get_terminal_size().lines

print('\n\n\n\n\n')

initial, remainder = data[:window_height], data[window_height:]

for line in initial:
    print(line, flush=True, end='')

for line in remainder:
    print(line, flush=True, end='')
    time.sleep(float(sys.argv[2]))
