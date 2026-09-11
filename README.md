# Spirochete AR poster companion

A marker-based AR experience for a scientific poster, built with
[AR.js](https://github.com/AR-js-org/AR.js) and A-Frame. A viewer points their
phone camera at a spiral marker printed on the poster and two microscopy
recordings play in place, anchored to the paper. No app install — it runs in
the mobile browser.

```
index.html          the AR experience
marker.html         printable marker, with a scale control
assets/marker/      spiro.patt (tracking descriptor) + spiro-marker.png
assets/video/       web-optimised MP4s that get served
vendor/             A-Frame 1.3.0 + AR.js 3.4.7, vendored deliberately
tools/              marker generator, video transcoder, HTTPS dev server
source-video/       original .mov masters (git-ignored)
```

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

The marker sits at the *top* of the callout deliberately — the video renders
1.8 marker-widths above the marker, so anything placed above it gets covered.
The dashed box shows the clear space to leave; it isn't printed.

At the default 80 mm marker the video renders about 192 mm wide, centred
144 mm above the marker, and the QR is ~50 mm (1.2 mm per module, comfortable
to scan at arm's length).

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
1 squares  1 seen          <- found a black quadrilateral
2 pattern  0.992 (need ≥0.60)  <- matched its interior to spiro.patt
```

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
