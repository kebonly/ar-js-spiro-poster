# Changelog

## [0.1.0] — 2026-09-10

Initial version: a marker-based AR companion for the spirochete poster.

### Added
- `index.html` — AR experience. Tracks a printed pattern marker and plays the
  microscopy recordings anchored to the poster, with a tap to switch clips.
- `marker.html` — printable marker with a millimetre scale control, verified to
  produce an exactly-sized black square at 100% print scale.
- `tools/make_marker.py` — generates the marker PNG and the `.patt` descriptor
  using only the standard library. Asserts the 16×16 pattern is distinct under
  all four rotations.
- `tools/transcode.sh` — re-encodes the masters to web-safe H.264
  (28 MB → 6.3 MB, 2.2 MB → 962 KB).
- `tools/serve.py` — HTTPS dev server, since camera access needs a secure
  origin and a LAN IP is not one.
- Vendored A-Frame 1.3.0 and AR.js 3.4.7.

### Notes
- `tools/transcode.sh` carries a `DYLD_FALLBACK_LIBRARY_PATH` workaround for a
  local ffmpeg linked against x265 4.2 after x265 was upgraded to 4.3. Remove
  it after `brew reinstall ffmpeg`.
