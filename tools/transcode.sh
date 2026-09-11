#!/usr/bin/env bash
# Transcode source .mov files into web-safe MP4s sized for use as WebGL video
# textures on phones. Targets H.264 main profile / yuv420p, which every mobile
# browser can decode in hardware.
#
# Workaround: this machine's ffmpeg is linked against libx265.216 (x265 4.2) but
# x265 has since been upgraded to 4.3 (libx265.217). The 4.2 keg is still on
# disk, so point dyld at it. Remove this line after `brew reinstall ffmpeg`.
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/Cellar/x265/4.2/lib:/opt/homebrew/lib

set -euo pipefail
cd "$(dirname "$0")/.."

encode() {
  local src="$1" out="$2" scale="$3"
  echo ">>> $src -> $out ($scale)"
  ffmpeg -y -v warning -stats -i "$src" \
    -an \
    -vf "scale=${scale}:flags=lanczos,fps=30,format=yuv420p" \
    -c:v libx264 -profile:v main -level 3.1 \
    -crf 26 -maxrate 1400k -bufsize 2800k \
    -preset slow -g 60 \
    -movflags +faststart \
    "$out"
}

encode source-video/spiro-cluster.mov            assets/video/spiro-cluster.mp4            720:720
encode source-video/spiro-flow-visualization.mov assets/video/spiro-flow-visualization.mp4 640:480

echo
echo "=== results ==="
ls -lh assets/video/
