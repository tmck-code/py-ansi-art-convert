#!/bin/bash

set -euo pipefail

artwork="$1"
official_png="$2"
width="$3"
time="${4:-60}"

artwork_basename=$(basename "$artwork" .ans)

rm -rf screenshots/
./ops/bin/scroll_and_screenshot.py "$artwork" "$width" demo.png
clear -x

if test -f "${artwork_basename}.16colors.mkv" \
  && ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${artwork_basename}.16colors.mkv" | grep -q "^${time}\.0*$"; then
  echo "Using cached ${artwork_basename}.16colors.mkv"
else
  echo "generating ${artwork_basename}.16colors.mkv"
  ffpb -loop 1 \
    -y \
    -i "$official_png" \
    -vf scale=1440:-2,crop=1440:1980:0:"'(ih-oh)*t/$time'" \
    -r 60 \
    -t "$time" \
    -c:v libx264 \
    -pix_fmt yuv420p \
    "${artwork_basename}.16colors.mkv"
fi

ffpb -loop 1 \
  -y \
  -i demo.png \
  -vf scale=1440:-2,crop=1440:1980:0:"'(ih-oh)*t/$time'" \
  -r 60 \
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
  -r 60 \
  "${artwork_basename}.combined.mp4"

mpv "${artwork_basename}.combined.mp4"

