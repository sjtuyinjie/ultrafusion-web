#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

encode_webm() {
  local input="$1"
  local output="${input%.mp4}.webm"
  if [[ -f "$output" ]]; then
    echo "skip existing: $output"
    return 0
  fi
  echo "encoding: $input"
  ffmpeg -y -hide_banner -loglevel error -i "$input" \
    -c:v libvpx-vp9 -crf 32 -b:v 0 -an -row-mt 1 \
    "$output"
}

videos=(
  "$ROOT/static/images/gs_4x.mp4"
  "$ROOT/assets/hkairport02.mp4"
  "$ROOT/assets/cbd.mp4"
  "$ROOT/assets/sysu.mp4"
  "$ROOT/static/videos/speed/dark.mp4"
  "$ROOT/static/videos/speed/corridor.mp4"
  "$ROOT/static/videos/speed/kaist.mp4"
  "$ROOT/static/videos/speed/eig1.mp4"
  "$ROOT/static/videos/speed/spx2.mp4"
  "$ROOT/static/videos/speed/arc2.mp4"
  "$ROOT/static/videos/speed/snow2.mp4"
  "$ROOT/static/videos/speed/multicam.mp4"
)

for video in "${videos[@]}"; do
  encode_webm "$video"
done

echo "done"
