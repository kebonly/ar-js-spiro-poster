# Changelog

## [0.3.0] — 2026-09-10

### Added
- Published to GitHub Pages at https://kebonly.github.io/ar-js-spiro-poster/
  (public repo; Pages on a free account cannot serve from a private one).
  Verified in production: every asset 200s with the right content type,
  `http://` 301-redirects to `https://`, MP4s honour Range requests (206), and
  the `moov` atom is in the first 3 KB so playback starts before the file
  finishes downloading.
- `print.html` — the poster callout: marker, QR code to the live URL, and the
  three steps a viewer follows, all sized in millimetres for 100%-scale
  printing. Marker is placed at the top of the callout because the video
  renders above it and would otherwise cover the instructions.
- Vendored `qrcode-generator` 1.4.4 for offline QR rendering. The generated QR
  was read back with an independent decoder (jsQR) to confirm it resolves to
  the exact live URL.

## [0.2.0] — 2026-09-10

### Added
- `?debug=1` diagnostic mode. Shows AR.js's thresholded detection image plus a
  telemetry panel that separates the two detection stages — "found a black
  square" vs "matched the pattern" — because they fail for entirely different
  reasons. Exposes `setArThreshold(0-255)` for binarisation problems.
- `tests/test_patt_encoding.py`, which pins our `.patt` rotation convention
  against AR.js's own `patt.hiro`.
- Troubleshooting section in the README.

### Fixed
- **`.patt` rotation convention was wrong at 90° and 270°.** Our encoder used
  `dx=y, dy=15-x` for the 90° block where AR.js uses `dx=15-y, dy=x`,
  effectively swapping the 90° and 270° blocks. The marker still detected, but
  reported the wrong orientation when held sideways — invisible on an upright
  poster, and confusing anywhere else. Caught by reconstructing all four
  reference blocks from `patt.hiro`.
- **Marker smoothing settings were silently ignored.** `<a-marker>` maps its
  attributes as kebab-case (`smooth-count`), so the camelCase `smoothCount`
  never applied and the defaults (5/2) were used instead of the intended
  (10/5). HTML attribute names being case-insensitive means this fails with no
  warning of any kind.

## [0.1.1] — 2026-09-10

### Fixed
- Camera feed appeared for a moment and then went black. The page set
  `background: #000` on both `html` and `body`. AR.js inserts the camera feed
  as a `z-index: -2` element on `<body>`, and in CSS paint order negative
  z-index descendants are painted *before* the backgrounds of in-flow
  block-level descendants — so the opaque `<body>` background covered the
  camera. The backdrop now lives on `html` only, with `body` transparent.

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
