#!/bin/bash

rm -rf screenshots/
./ops/scroll_and_screenshot.py tmp/artANSI/goto80-goto437.ansi goto437.png

ffmpeg -loop 1 \
  -i goto80-goto437.ans.png \
  -vf scale=1440:-2,crop=1440:1980:0:'(ih-oh)*t/10' \
  -t 10 \
  -c:v libx264 \
  -pix_fmt yuv420p \
  goto80.16colors.mkv

ffmpeg -loop 1 \
  -i goto437.png \
  -vf scale=1440:-2,crop=1440:1980:0:'(ih-oh)*t/10' \
  -t 10 \
  -c:v libx264 \
  -pix_fmt yuv420p \
  goto80.mine.mkv

ffpb \
  -i output.16colors.mkv \
  -i output.mkv \
  -filter_complex [0:v][1:v]hstack[v] \
  -map [v] \
  goto437.combined.mp4
