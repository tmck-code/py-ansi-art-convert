#!/bin/bash

set -euo pipefail

artwork="$1"
official_png="$2"
time="${3:-60}"

artwork_basename=$(basename "$artwork" .ans)

rm -rf screenshots/
./bin/scroll_and_screenshot.py "$artwork" demo.png

ffpb -loop 1 \
  -y \
  -i "$official_png" \
  -vf scale=1440:-2,crop=1440:1980:0:"'(ih-oh)*t/$time'" \
  -t "$time" \
  -c:v libx264 \
  -pix_fmt yuv420p \
  "${artwork_basename}.16colors.mkv"

ffpb -loop 1 \
  -y \
  -i demo.png \
  -vf scale=1440:-2,crop=1440:1980:0:"'(ih-oh)*t/$time'" \
  -t "$time" \
  -c:v libx264 \
  -pix_fmt yuv420p \
  "${artwork_basename}.mine.mkv"

ffpb \
  -y \
  -i "${artwork_basename}.16colors.mkv" \
  -i "${artwork_basename}.mine.mkv" \
  -filter_complex [0:v][1:v]hstack[v] \
  -map [v] \
  "${artwork_basename}.combined.mp4"

mpv "${artwork_basename}.combined.mp4"