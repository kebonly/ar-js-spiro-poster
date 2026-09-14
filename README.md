# Spirochete AR poster companion

A marker-based AR experience for a scientific poster, built with
[AR.js](https://github.com/AR-js-org/AR.js) and A-Frame. A viewer points their
phone camera at a marker printed on the poster and the microscopy recording
for that figure plays in place, anchored to the paper. No app install — it runs
in the mobile browser.

Eight movies, each with its own printed barcode marker, plus a spiral marker
that cycles through all of them.

```
config.js              the movie list and layout — the one file to edit
index.html             the AR experience
print.html             poster callout + one printable marker per movie
marker.html            the spiral marker on its own, with a scale control
assets/marker/         spiro.patt (tracking descriptor) + spiro-marker.png
assets/marker/barcode/ barcode-0.png … barcode-7.png (generated)
assets/video/          web-optimised MP4s that get served
vendor/                A-Frame 1.3.0 + AR.js 3.4.7 + qrcode-generator
tools/                 marker generators, video transcoder, HTTPS dev server
tests/                 encoding checks for both marker families
source-video/          original masters, pre-compression (git-ignored)
```

## How the markers work

There are two kinds of marker on the poster, and they do different jobs:

| | Spiral marker | Barcode markers |
|---|---|---|
| Kind | pattern (`spiro.patt`) | matrix code, `3x3_HAMMING63` |
| Shows | all clips, with a switcher | exactly one clip each |
| How many | one | up to 8 (ids 0–7) |
| Needs a `.patt` | yes | no — the id is read straight off the grid |

Both run at once via AR.js's `detectionMode: mono_and_matrix`, and both use the
same `patternRatio: 0.5` (a 25% black border each side), which is why a single
global setting serves them.

**The QR code is not a marker.** It is only how a viewer loads the page, so it
goes on the poster **once** — not beside every figure. Barcode markers are what
each figure gets.

## Running it locally

Camera access requires a secure origin. `localhost` counts as one, a LAN IP
does not — so testing on a real phone needs HTTPS:

```bash
python3 tools/serve.py
```

This prints a `https://<your-lan-ip>:8443/` URL for the phone. It uses a
self-signed certificate, so you will get a warning to tap through. For a
warning-free test, tunnel instead:

```bash
cloudflared tunnel --url http://localhost:8000
```

## Live site

**https://kebonly.github.io/ar-js-spiro-poster/**

Served from `main` / root by GitHub Pages, with HTTPS enforced and `http://`
301-redirecting to `https://` — which matters, because browsers only grant
camera access on a secure origin.

Deploying is just pushing:

```bash
git push
```

A push takes a minute or so to go live. Note the repository is **public**;
GitHub Pages on a free account cannot serve from a private repo, so the
microscopy MP4s are publicly fetchable.

## Putting it on the poster

Open [`print.html`](print.html). It builds the callout that goes on the
poster: the marker, a QR code to the live URL, and the three steps a viewer
needs. Set the marker size in millimetres and print **at 100% scale**.

The spiral marker sits at the *top* of its callout deliberately — its video
renders 1.8 marker-widths above it, so anything placed above gets covered. A
**barcode** marker's video is centred *on* the marker instead, so its dashed
box is a halo all round rather than a box overhead.

At an 80 mm marker the video renders about **320 mm** wide (`width: 4.0`), and
the QR is ~50 mm (1.2 mm per module, comfortable to scan at arm's length).

The dashed area is what the video **covers on screen**, not something that must
be blank on the poster — it is an overlay, so it just hides what's underneath
while a viewer watches. Use it to decide where a marker goes. If it is bigger
than you want, print that marker smaller (the video scales with it) or lower
`LAYOUT.width`.

Change the URL field if you ever move the site — the QR regenerates live.

## Printing the marker

Open `marker.html`, set the black-square width (80 mm is a good default), and
print **at 100% scale** with "fit to page" turned off.

Two things people get wrong:

- **Do not crop the white margin.** The quiet zone around the black square is
  part of the marker; the detector needs it.
- **Avoid glossy lamination.** Spotlight glare off a glossy poster is the most
  common reason tracking fails at a conference.

An 80 mm square tracks from roughly 0.4–1.2 m. Scaling the marker up scales the
range roughly proportionally — and scales the video with it, since the layout is
expressed in marker widths.

## Adjusting the layout

Everything you'd normally want to change sits in one `LAYOUT` block at the
top of [`config.js`](config.js):

```js
var LAYOUT = {
  width:       4.0,    // video width
  offsetAbove: 1.8,    // height of the video's centre above the marker
  bezelPad:    0.16    // border visible around the video
};
```

**All distances are in marker widths**, where `1.0` is the printed width of
the black square — not centimetres, not pixels. This is the important bit: the
layout is resolution- and scale-independent, so printing the marker at a
different size scales the video with it and nothing else needs touching.

At the default 80 mm marker:

| Setting | Value | On the poster |
|---|---|---|
| `width: 4.0` | 4.0 × 80 mm | video ~320 mm wide |
| `offsetAbove: 1.8` | 1.8 × 80 mm | centre ~144 mm above the marker (spiral only; barcode markers use 0) |

So to make the video half as big, set `width: 2.0`. To sit it closer to the
marker, lower `offsetAbove`. Only the height is derived — it comes from each
clip's own aspect ratio, so the video is never stretched.

`print.html` reads the same numbers back to you in millimetres as you change
the marker size, and the dashed clearance box grows to match.

### Pinch to resize, on the phone

Viewers can **pinch with two fingers** to scale the video between 0.4× and 3×
of `LAYOUT.width`. A readout appears while pinching, the choice is remembered
in `localStorage`, and a **Reset size** chip appears whenever the size has been
changed. A single tap cycles to the next clip; a drag does not.

The readout's second line shows the resulting `LAYOUT.width`:

```
1.60×
LAYOUT.width 3.84
```

That's deliberate — pinch until it looks right on the printed poster, read the
number off, and paste it into `LAYOUT.width` to make it the default for
everyone. Beats guessing and re-deploying.

Gestures are handled with pointer events on the canvas rather than through
A-Frame's raycaster. A-Frame only emits `click` on entities when the camera
has a `cursor` component, which AR.js scenes don't set up — so raycaster-based
taps silently never fire. Doing it at the DOM level also keeps pinch and tap
in one state machine, so a pinch can't also register as a tap.

## Adding another movie

Drop the `.mp4` in `assets/video/` and add **one entry** to `CLIPS` in
[`config.js`](config.js):

```js
var CLIPS = [
  { key: 'cluster', label: 'Cluster', barcode: 1,
    src: 'assets/video/spiro-cluster.mp4' },
  { key: 'flow',    label: 'Flow',    barcode: 0,
    src: 'assets/video/spiro-flow-visualization.mp4' },
  { key: 'motility', label: 'Motility', barcode: 2,        // <- new
    src: 'assets/video/spiro-motility.mp4' }
];
```

That's the whole change. Generated from this one list: the `<video>` element,
its **barcode marker**, the switcher button, the iOS gesture-unlock list, the
tap-to-cycle order, and the printable marker sheet in `print.html`. The aspect
ratio is read from the file itself. Nothing has to be kept in sync by hand —
which is why `config.js` is shared by both pages rather than duplicated.

`barcode` is what gives a movie its own marker. Valid ids are **0–7**; print
the matching `assets/marker/barcode/barcode-<id>.png` from `print.html`. Omit
`barcode` and the movie is still reachable through the spiral marker's
switcher, just without a marker of its own.

**Always run new clips through the transcoder.** Drop the original in
`source-video/` and run:

```bash
./tools/transcode.sh          # everything in source-video/
python3 tests/test_config.py  # checks the mapping and the encodes
```

Do not point `config.js` at a video straight out of your imaging software.
Four properties matter, and three of them fail in ways you cannot diagnose
from the phone:

| | Why |
|---|---|
| `yuv420p` | iOS/Android H.264 decoders are 4:2:0 only. A `yuv444p` file plays fine on your laptop and **refuses to play on iPhone**. |
| `+faststart` | Puts the moov atom at the front. Without it the browser downloads nearly the whole file just to read the dimensions, which defeats `preload="metadata"` and the lazy per-marker loading entirely. |
| no audio | Muted video is what lets iOS autoplay into a WebGL texture. |
| ≤720 px | These are textures a few cm across. A 3024 px source costs 21 MB of GPU memory to show at that size. |

`tests/test_config.py` checks all of this, plus duplicate/out-of-range barcode
ids and missing files. Run it after editing `config.js` — a hand-edited entry
missing its closing `},` makes the whole file unparseable, and the page then
dies on load rather than degrading.

Encode the new clip the same way as the others so it behaves on mobile:

```bash
ffmpeg -i input.mov -an \
  -vf "scale=720:-2:flags=lanczos,fps=30,format=yuv420p" \
  -c:v libx264 -profile:v main -level 3.1 \
  -crf 26 -maxrate 1400k -bufsize 2800k -preset slow -g 60 \
  -movflags +faststart \
  assets/video/spiro-motility.mp4
```

Two things worth knowing:

- **Keep it silent** (`-an`) unless you actually need audio. Muted video is
  what lets iOS autoplay it into a WebGL texture without a fight.
- **Watch the total payload.** Everything is fetched over conference wifi.
  The two current clips are ~7 MB combined; a third of similar length is
  fine, ten would not be.

Buttons are laid out with flexbox and will shrink to fit, but past about four
the labels get cramped on a phone.

## Troubleshooting marker detection

Open the page with `?debug=1`:

```
https://<your-url>/index.html?debug=1
```

This turns on a telemetry panel plus AR.js's own debug view, which renders the
**thresholded black-and-white image** that detection actually runs on. That
view is the single most useful thing here — if the marker doesn't appear as a
clean black square in it, no amount of fiddling elsewhere will help.

The panel splits detection into its two real stages, because they fail for
completely different reasons:

```
codes      3x3_HAMMING63 OK  ratio 0.50   <- the marker family took effect
1 squares  3 seen                         <- found 3 black quadrilaterals
2a pattern id 0  0.980 (need ≥0.60)       <- one matched spiro.patt
2b barcode id 1  1.000 (need ≥0.60)       <- one decoded as barcode 1
   ids     0×111  1×111                   <- which ids decoded recently
   unknown 0   conflicts 0
markers
  spiral     FOUND  5.64 mw  cluster
  barcode-1  FOUND  6.44 mw  cluster
  barcode-0  FOUND  6.79 mw  flow
playing    cluster flow
```

Four of those rows exist for specific failure modes:

- **`codes`** reads the marker family back out of AR.js. If `matrixCodeType`
  is mis-cased, AR.js logs a `console.assert` (which does nothing) and then
  calls `setMatrixCodeType(undefined)`, leaving barcode detection quietly
  dead. This row turns that into a visible red line.
- **`ids`** is the row that matters for barcodes. A misread doesn't fail — it
  decodes as a *different id*. This tells you whether your printed square
  really is the number you think it is.
- **`unknown`** counts squares that decoded as neither: the signature of a
  wrong `patternRatio`, or a barcode outside the configured family.
- **`conflicts`** counts squares where both a pattern id and a matrix id were
  found. AR.js resolves those in favour of the pattern, so a non-zero number
  here means a barcode marker may be getting swallowed.

**If stage 1 says `none`** — ARToolKit can't even find a black square. This is
almost always physical, not code:

| Cause | What to do |
|---|---|
| Glare from overhead lights | Tilt the poster or move. Matte stock is the real fix. |
| Too far away | An 80 mm marker works to roughly 1.2 m. Get closer, or print bigger. |
| Too dark / too blown out | Adjust the binarisation: `setArThreshold(60)` or `setArThreshold(160)` in the console. Default is 100. |
| Quiet zone cropped | The white margin is part of the marker. Don't trim to the black square, and don't place it on a dark background. |
| Marker bent or curling | It must be flat. A curled corner breaks the quadrilateral. |
| Too oblique | Detection wants roughly within 60° of face-on. |

**If stage 1 finds squares but stage 2 stays below 0.60** — the square is
found but its interior doesn't match the pattern. Now it's a configuration
problem:

- **`patternRatio` mismatch.** Ours is `0.5` and the printed marker has a
  border 1/4 of the square's width on each side. If you regenerate the marker
  with different proportions, this must change to match.
- **Wrong or stale `.patt`.** Confirm `assets/marker/spiro.patt` returns HTTP
  200 and contains 3072 numbers. If you edited the marker art, rerun
  `tools/make_marker.py` — printing a new marker against an old `.patt` fails
  exactly this way.
- **Marker too small in frame** to resolve the interior. The pattern is only
  16×16; a marker under ~40 px in the camera image can be found as a square
  but not identified.

**If both stages pass but nothing renders**, it's the scene, not tracking.
Check `distance` in the panel — if it reads something plausible (1–4
marker-widths), the pose is fine and the video plane is simply out of frame.
It sits 1.8 marker-widths *above* the marker, so at close range it's off the
top of the screen. Back away.

**If a barcode marker isn't recognised**, work down this list:

1. Is `codes` green? If not, `matrixCodeType` is wrong and no barcode will ever
   decode.
2. Does `ids` show anything at all? If squares are seen but no ids decode, the
   marker is probably too small in frame — a 3×3 grid needs less resolution
   than a 16×16 pattern, but it still needs the cells distinguishable.
3. Does `ids` show the *wrong* number? Then the printed marker isn't the one
   you think. Re-print from `print.html`, which is generated from the same
   config the app reads.
4. Is `conflicts` climbing? A pattern marker in the same frame may be winning
   the classification. Try framing the barcode alone.

### Regenerating the barcode markers

```bash
python3 tools/make_barcode_markers.py
python3 tests/test_barcode_table.py
```

The generator writes all 8 markers and self-checks them; the test pins the bit
patterns against the canonical ARToolKit markers. That test exists because the
failure mode is nasty — a wrong bit layout produces a marker that decodes to a
*different valid id*, so the poster plays the wrong movie with no error
anywhere.

The markers are generated rather than downloaded for two reasons: the
widely-linked collection they come from declares no licence, and its images
have no white quiet zone (they are black to the corners), which invites
cropping them flush and breaking detection. Ours bake the quiet zone in, using
the same geometry as the spiral marker so one print rule sizes both.

### Things that bit us here

- **A black `<body>` background hides the camera feed entirely** — feed flashes
  on, then goes black. See the note in the changelog; AR.js puts the camera at
  `z-index: -2`.
- **`<a-marker>` attributes are kebab-case.** `smooth-count`, not
  `smoothCount`. HTML attribute names are case-insensitive, so the camelCase
  form is silently ignored and you get the default with no warning.
- **The `.patt` rotation convention is not arbitrary.** Getting it wrong still
  detects the marker but reports the wrong rotation at 90°/270°, which a
  wall-mounted poster would never reveal.
  `tests/test_patt_encoding.py` pins this against AR.js's own `patt.hiro`.
- **`matrixCodeType` is case-sensitive and fails silently.** It must be
  `3x3_HAMMING63` — not `3x3_hamming_6_3` (the folder name the markers come
  from) and not `3x3_parity65`. A miss logs a `console.assert` and disables
  barcode detection with no other symptom. The `codes` row in `?debug=1`
  exists to catch it.
- **Two markers swapping into the same screen pixels can latch.** ARToolKit
  tracks squares frame to frame, so a square already identified as the pattern
  marker keeps that identity if a different marker appears in exactly the same
  place. Real panning breaks the continuity and it resolves; it only showed up
  in synthetic testing where one marker was teleported onto another.

## Regenerating assets

The marker generator is pure stdlib Python (no PIL/numpy):

```bash
python3 tools/make_marker.py
```

It writes both the printable PNG and the `.patt`, then prints the 16×16 grid as
the tracker sees it and asserts that the four rotations are distinct. That
assertion is the point of the script: a pattern that is near-symmetric under
rotation makes the video flip orientation between frames, and the failure is
confusing to debug after the fact.

To re-encode the videos from the masters in `source-video/`:

```bash
./tools/transcode.sh
```

Both clips are silent, so they are encoded without an audio track — which also
means muted autoplay works cleanly on iOS.

| | source | served |
|---|---|---|
| `spiro-cluster` | 28 MB, 1000×1000, 40 fps | 6.3 MB, 720×720, 30 fps |
| `spiro-flow-visualization` | 2.2 MB, 724×544, 50 fps | 962 KB, 640×480, 30 fps |

### A note on this machine's ffmpeg

`tools/transcode.sh` sets `DYLD_FALLBACK_LIBRARY_PATH` as a workaround. The
installed ffmpeg was linked against x265 4.2 (`libx265.216.dylib`), but x265 has
since been upgraded to 4.3 (`libx265.217.dylib`), so ffmpeg fails to launch. The
4.2 keg is still on disk, so pointing dyld at it works. The real fix is:

```bash
brew reinstall ffmpeg
```

After that, the `export` line at the top of the script can be deleted.

## Implementation notes

- **Libraries are vendored, not CDN-loaded.** Conference wifi is unreliable and
  a CDN miss would break the poster in front of an audience. A-Frame 1.3.0 with
  AR.js 3.4.7 is a known-good pairing; newer A-Frame releases have regressions
  against AR.js 3.4.x.
- **The "Start camera" screen is load-bearing.** iOS Safari will not let a
  `<video>` feed a WebGL texture unless `play()` was called inside a real user
  gesture. The tap unlocks *both* clips (play, then immediately pause) so the
  second one isn't black when switched to.
- **The scene lives in a `<template>` until that tap.** AR.js opens the camera
  the moment the scene initialises, so leaving `<a-scene>` in the document
  fires the permission prompt on page load, before the viewer has any idea why
  the page wants their camera. Injecting the scene on tap gives AR.js an
  ordinary first-time startup, just deferred.
- **The videos are not in `<a-assets>`.** A-Frame blocks scene startup until
  assets report ready, and these clips stalled it for the full 10 s timeout.
  A-Frame resolves a `#id` material `src` with `querySelector`, so plain DOM
  video elements work and load in the background instead.
- **Layout is in marker units.** Inside `<a-marker>`, 1 unit = the printed width
  of the black square, so the video stays correctly proportioned at any print
  size. Marker-local axes: +X right across the poster, +Y out of the paper, −Z
  up the poster.
- **Marker smoothing is turned up.** Raw pose estimates jitter a few degrees per
  frame — barely visible on a small object, very obvious on a large video plane.
- **Video pauses when the marker leaves frame**, so someone who looks away and
  back resumes rather than missing content.
