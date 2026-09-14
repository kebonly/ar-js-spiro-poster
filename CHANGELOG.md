# Changelog

## [0.7.0] — 2026-09-13

All eight movies are now wired up, one per barcode marker (0-7).

### Fixed
- **Six of the eight clips were not poster-safe.** They were added straight
  from the imaging pipeline rather than through `tools/transcode.sh`:
  - `density_vs_time.mp4` was **yuv444p**. iOS and Android H.264 decoders are
    4:2:0 only, so it would have played on a laptop and refused on an iPhone.
  - Six lacked `+faststart`. `density_vs_time` had its moov atom at byte
    1,456,124 of 1,468,927, and `spiro-napari` at 9,817,875 of 9,821,700 —
    99%+ of each file. Since `preload="metadata"` reads the moov atom for the
    dimensions, this quietly defeated the lazy per-marker loading: page load
    would have pulled almost everything.
  - `spiro-napari` was 3024x1840, about 21 MB of GPU memory for a plane a few
    centimetres across.
  - `spiro-couette` carried an unused AAC track.

  All re-encoded. Originals preserved in the git-ignored `source-video/`.
  Total payload **36.9 MB -> 11.9 MB**.
- **The switcher overflowed the screen with eight clips.** It was a single
  non-wrapping flex row built for two or three buttons; at eight, buttons ran
  off both edges of a phone and most were unreachable with no sign they
  existed. Now wraps (3 rows at 375px) with every label fully visible.

### Added
- `tests/test_config.py` — validates `config.js` and the files it points at:
  parses it with `node --check`, then checks barcode ids are integers 0-7,
  that none are duplicated (two markers on one id render overlapping video
  planes with no error), that every `src` exists, and that each file is
  yuv420p with the moov atom at the front. The faststart check is pure stdlib
  so it works without ffmpeg.
- `tools/transcode.sh` generalised: processes everything in `source-video/`
  (or named files), caps the longest edge, strips audio, forces yuv420p and
  faststart, and verifies every output before exiting non-zero on a problem.

## [0.6.1] — 2026-09-13

### Fixed
- **No video appeared over any marker.** Markers tracked correctly and the
  "point at a marker" hint disappeared, but nothing rendered.

  `buildMarker` set the screenRoot position with an object,
  `setAttribute('position', {x: 0, y: 0.01, z: -offset})`, and it runs *before*
  the marker is in the document. A-Frame stringifies an object value on an
  uninitialised entity to `"[object Object]"`, parses that back as `NaN NaN`,
  and defaults the missing third component to 0. A NaN transform silently stops
  the entire subtree rendering — while the marker still tracks and markerFound
  still fires, which is exactly what makes it look like a marker that works but
  shows nothing.

  Introduced in 0.6.0: before that refactor the position was set in `ready()`,
  after the scene was live, where the object form parses fine. Now passed as a
  string, which is safe either way.

  This was not caught earlier because 0.6.0 was verified by reading state
  programmatically — `playing`, marker visibility, `cfMatrix` — and never by
  looking at a rendered frame. The one screenshot that would have shown it was
  misread as a cropped preview pane.

### Changed
- A barcode marker's video is now centred **on** its marker
  (`BARCODE_LAYOUT.offsetAbove = 0`) rather than 1.8 marker-widths above it.
  The old offset suits the spiral marker, which has dedicated clear space above
  it on the poster; a barcode marker sits beside a figure with no such space,
  and at any normal phone distance 1.8 widths up is off the top of the screen.
  Tracking is unaffected by the video covering the marker — detection runs on
  the raw camera image, not on what we draw over it.
- Layout is now per-marker: `LAYOUT` is the base, `BARCODE_LAYOUT` overrides it
  for barcode markers, and an optional per-clip `layout` overrides again.
- `print.html` shows barcode markers with a dashed halo *around* the marker
  (~205mm at an 80mm marker) instead of a clearance box above it, matching
  where the video now appears. The spiral keeps its clearance-above box.

## [0.6.0] — 2026-09-13

### Added
- **One marker per movie.** Barcode (matrix-code) markers from the
  `3x3_HAMMING63` family run alongside the existing spiral pattern marker, via
  AR.js's `detectionMode: mono_and_matrix`. Pointing at a barcode marker plays
  exactly one clip; the spiral keeps showing all clips with the switcher. Up to
  8 markers (ids 0-7). Verified that both modalities detect in the same
  session, individually and with all three markers in one frame.
- `tools/make_barcode_markers.py` generates all 8 markers with a white quiet
  zone baked in, reusing the geometry and PNG writer from `make_marker.py` so
  both families print at the same scale and share one `patternRatio`.
  Generated rather than downloaded: the widely-linked collection declares no
  licence, its images have no quiet zone, and the encoding is mechanical (three
  fixed orientation cells, six data cells).
- `tests/test_barcode_table.py` pins the bit patterns against the canonical
  ARToolKit markers, and independently asserts the family's minimum pairwise
  cell distance is 3. A wrong bit layout would decode to a *different valid
  id* — the poster would play the wrong movie with no error anywhere.
- `config.js`, shared by `index.html` and `print.html`, so adding a movie stays
  a genuine one-line change and the printed markers cannot drift from what the
  app looks for.
- `print.html` gains a marker-per-movie sheet, generated from the same config,
  each block labelled with its movie and barcode id. The QR block stays, and is
  now explicitly marked as print-once — it is the page entry point, not a
  tracking marker.
- Diagnostics gained four rows for failure modes that were previously invisible:
  `codes` (reads the marker family back out of AR.js), `ids` (which barcode ids
  decoded — a misread shows up as a *different* id, not as a failure),
  `unknown`, and `conflicts`. Plus a per-marker visibility table.

### Changed
- The single marker became N. Marker subtrees are cloned from a `<template>`
  and built into the scene fragment before it enters the document; per-marker
  state replaced the module-level `marker`/`screenEl`/`bezel`/`markerVisible`
  singletons.
- **Playback is now derived, not per-marker.** A clip plays iff at least one
  visible marker is showing it, recomputed from scratch on every change. This
  is required because clips are shared: the spiral can show `flow` while
  barcode 0 also shows it, and the old `markerLost -> pause()` would have
  killed playback the other marker still needed. Verified: losing the spiral
  leaves the clip playing for barcode 0, without restarting it.
- Switcher and tap-to-cycle are scoped to the spiral marker and hidden while
  only a barcode marker is visible — a barcode marker has one clip, so buttons
  would silently do nothing. Button highlight is now derived rather than
  pushed, so it can't lie after looking at another marker.
- Clips are `preload="metadata"` instead of `"auto"`. Eight clips at `auto`
  would download in full on page load. `metadata` rather than `none` because
  the plane needs `videoWidth`/`videoHeight` to be shaped correctly, and the
  moov atom is at the front of the file already.
- Pinch-zoom applies to every marker; gate and hint copy no longer say "the
  spiral marker".
- Dropped the inert `emitevents` attribute (no mapping exists in AR.js 3.4.7).

## [0.5.0] — 2026-09-10

### Added
- Pinch-to-resize. Two fingers scale the video between 0.4x and 3x of
  `LAYOUT.width`, clamped, remembered in `localStorage`, with a "Reset size"
  chip offered whenever the size has been changed. The readout shows the
  resulting `LAYOUT.width` so a size found by pinching can be pasted back into
  the config and made the default.

### Fixed
- **Tap-to-cycle never worked on a real device.** It relied on A-Frame
  emitting `click` on the video plane, but A-Frame only does that when the
  camera carries a `cursor` component, which AR.js scenes don't set up. An
  earlier test appeared to confirm the feature only because it fired
  `emit('click')` synthetically, which exercised the handler without
  exercising the path a real touch takes.

  Taps and pinches are now both handled with pointer events on the canvas, in
  one gesture state machine — so a pinch cannot also register as a tap, and a
  drag doesn't switch clips. Removed the `raycaster` / `.clickable` config
  that implied an interaction that never existed.
- iOS Safari ignores `user-scalable=no`, so `gesturestart`/`gesturechange`/
  `gestureend` are now cancelled explicitly to stop the browser pinch-zooming
  the whole page instead of the video.

## [0.4.0] — 2026-09-10

### Changed
- Layout is now driven by a single `LAYOUT` block (`width`, `offsetAbove`,
  `bezelPad`), all expressed in marker widths so the poster layout stays
  scale-independent. Previously the video width lived in the clip table and
  the vertical offset was hardcoded in the scene markup.
- Clips are declared once in a `CLIPS` list. The `<video>` element, the
  switcher button, the gesture-unlock list and the tap-to-cycle order are all
  generated from it; adding a movie previously meant editing four places that
  had to be kept in sync by hand.
- Clip aspect ratio is read from the file's own metadata instead of being
  hand-entered, so a mistyped ratio can no longer stretch a video.
- Tapping the video cycles through all clips and wraps, rather than toggling
  between exactly two.

Verified by temporarily adding a third clip: three buttons and three video
elements were generated, and the tap cycle wrapped correctly.

## [0.3.1] — 2026-09-10

### Fixed
- Scattered translucent navy blocks appeared over the video while tracking.
  The backing plate sat only 0.005 marker-widths behind the video plane, and
  AR.js's projection uses near=0.005 / far=10000 — a ratio of 2,000,000, which
  leaves very little usable depth precision. The two planes fought for the
  depth test and the plate won in patches.

  Fixed three ways, because a larger gap alone is not enough: depth resolution
  degrades with the *square* of viewing distance, so a fixed world-space gap
  that works up close can fail when someone steps back.
  1. Real geometric gap widened to 0.04 marker-widths (~3 mm at an 80 mm
     marker; invisible from the front).
  2. New `depth-bias` component applies `polygonOffset`, which works in
     depth-buffer units and therefore holds at any distance.
  3. Backing plate is now opaque instead of 0.92 alpha, so it sorts into the
     opaque pass and draws *before* the video rather than after it.

  Verified clean at 8.7, 10.5 and closer distances, on both clips.

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
