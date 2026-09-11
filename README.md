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

## Deploying to GitHub Pages

```bash
gh repo create ar-js-spiro-poster --public --source=. --push
```

Then in the repository: **Settings → Pages → Source: Deploy from a branch →
`main` / `(root)`**. The site appears at
`https://<user>.github.io/ar-js-spiro-poster/` within a minute or two. GitHub
Pages serves HTTPS by default, which is all AR.js needs.

Generate a QR code pointing at that URL and print it next to the marker — that
is how people will actually find the page.

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
