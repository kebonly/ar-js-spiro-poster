#!/usr/bin/env bash
# Transcode every master in source-video/ into a web-safe MP4 in assets/video/.
#
# Four properties matter for a poster, and getting any of them wrong fails in a
# way that is hard to diagnose from the phone:
#
#   yuv420p     iOS and Android hardware H.264 decoders support only 4:2:0.
#               A yuv444p file simply refuses to play on iPhone.
#   +faststart  Puts the moov atom at the FRONT. Without it the browser must
#               download almost the entire file before it can even report the
#               video's dimensions -- which defeats preload="metadata" and the
#               lazy per-marker loading the app relies on.
#   no audio    Muted video is what lets iOS autoplay into a WebGL texture.
#               An audio track is dead weight here.
#   modest size These are textures a few centimetres across on a poster. A
#               3024px source costs 21 MB of GPU memory to show at that size.
#
# Usage:
#   ./tools/transcode.sh              # everything in source-video/
#   ./tools/transcode.sh a.mov b.mp4  # just these files
#
# Workaround: this machine's ffmpeg is linked against libx265.216 (x265 4.2) but
# x265 has since been upgraded to 4.3 (libx265.217). The 4.2 keg is still on
# disk, so point dyld at it. Remove this line after `brew reinstall ffmpeg`.
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/Cellar/x265/4.2/lib:/opt/homebrew/lib

set -euo pipefail
cd "$(dirname "$0")/.."

MAX_DIM=${MAX_DIM:-720}     # longest edge, in pixels
FPS=${FPS:-30}
CRF=${CRF:-26}
MAXRATE=${MAXRATE:-1400k}

encode() {
  local src="$1"
  local out="assets/video/$(basename "${src%.*}").mp4"
  echo ">>> $(basename "$src") -> $(basename "$out")"

  # Cap the longest edge while preserving aspect, then force even dimensions
  # (H.264 requires them, and odd sizes make libx264 fail outright).
  ffmpeg -y -v warning -stats -i "$src" \
    -an \
    -vf "scale='min(${MAX_DIM},iw)':'min(${MAX_DIM},ih)':force_original_aspect_ratio=decrease:flags=lanczos,\
scale=trunc(iw/2)*2:trunc(ih/2)*2,\
fps=${FPS},format=yuv420p" \
    -c:v libx264 -profile:v main -level 3.1 \
    -crf "${CRF}" -maxrate "${MAXRATE}" -bufsize "$((${MAXRATE%k} * 2))k" \
    -preset slow -g $((FPS * 2)) \
    -movflags +faststart \
    "$out"
}

if [ "$#" -gt 0 ]; then
  for f in "$@"; do encode "$f"; done
else
  shopt -s nullglob
  for f in source-video/*.mov source-video/*.mp4 source-video/*.avi source-video/*.mkv; do
    encode "$f"
  done
fi

echo
echo "=== verifying every output is poster-safe ==="
fail=0
printf "%-34s %-8s %-9s %-11s %-5s %-6s %s\n" FILE CODEC PIXFMT SIZE AUDIO SIZE FASTSTART
for out in assets/video/*.mp4; do
  # Read key=value, not positional CSV: ffprobe emits fields in the stream's
  # own order, not the order you asked for, so positional parsing silently
  # transposes columns.
  probe=$(ffprobe -v error -select_streams v:0 \
      -show_entries stream=codec_name,pix_fmt,width,height \
      -of default=noprint_wrappers=1 "$out")
  codec=$(sed -n 's/^codec_name=//p' <<<"$probe")
  pf=$(sed -n 's/^pix_fmt=//p' <<<"$probe")
  w=$(sed -n 's/^width=//p' <<<"$probe")
  h=$(sed -n 's/^height=//p' <<<"$probe")
  aud=$(ffprobe -v error -select_streams a -show_entries stream=codec_name -of csv=p=0 "$out" | head -1)
  [ -z "$aud" ] && aud="none"
  if head -c 4000 "$out" | strings | grep -q moov; then fs="yes"; else fs="NO"; fi
  mb=$(echo "scale=1; $(stat -f%z "$out")/1048576" | bc)
  printf "%-34s %-8s %-9s %-11s %-5s %-6s %s\n" \
    "$(basename "$out")" "$codec" "$pf" "${w}x${h}" "$aud" "${mb}MB" "$fs"
  [ "$pf" = "yuv420p" ] || { echo "   ^ FAIL: pix_fmt must be yuv420p"; fail=1; }
  [ "$fs" = "yes" ]     || { echo "   ^ FAIL: moov atom is not at the front"; fail=1; }
  [ "$aud" = "none" ]   || { echo "   ^ warn: has an audio track"; }
done
echo
total=$(echo "scale=1; $(cat assets/video/*.mp4 | wc -c)/1048576" | bc)
echo "total payload: ${total} MB"
exit $fail
