#!/usr/bin/env python3
"""Validate config.js and the video files it points at.

Everything checked here has already gone wrong at least once, and each failure
mode is quiet — the page either dies on load or misbehaves on a phone with no
error anywhere:

  syntax        A hand-edited CLIPS entry missing its closing "}," makes the
                whole file unparseable, so window.SPIRO_AR is undefined and
                index.html throws on its first line. Dead page, not a degraded
                one.
  barcode range 3x3_HAMMING63 only encodes ids 0-7. AR.js accepts anything and
                silently never matches.
  duplicates    Two clips sharing a barcode produce two markers with the same
                id, both matching the same printed square, and two video
                planes drawn on top of each other. No error.
  pix_fmt       iOS/Android H.264 decoders are 4:2:0 only. A yuv444p file
                refuses to play on iPhone while working fine on a desktop.
  faststart     With the moov atom at the end of the file, the browser must
                download nearly all of it just to read the dimensions, which
                defeats preload="metadata" and the lazy per-marker loading.

Run:  python3 tests/test_config.py
ffprobe is used when available; the structural checks work without it.
"""

import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.js"
MAX_BARCODE = 7          # 3x3_HAMMING63 provides ids 0-7
SIZE_WARN_MB = 8.0

failures = []
warnings = []


def fail(msg):
    failures.append(msg)
    print(f"  FAIL  {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  warn  {msg}")


def ok(msg):
    print(f"  ok    {msg}")


def load_config():
    """Parse config.js by running it in node, so we test the real file."""
    if not shutil.which("node"):
        print("node not found; cannot parse config.js")
        sys.exit(2)

    syntax = subprocess.run(["node", "--check", str(CONFIG)],
                            capture_output=True, text=True)
    if syntax.returncode != 0:
        fail("config.js does not parse:\n" +
             "\n".join("        " + l for l in syntax.stderr.splitlines()[:6]))
        return None
    ok("config.js parses")

    script = (
        "global.window = {};"
        f"require({json.dumps(str(CONFIG))});"
        "process.stdout.write(JSON.stringify(global.window.SPIRO_AR));"
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    if out.returncode != 0:
        fail("config.js threw while loading: " + out.stderr.strip()[:200])
        return None
    return json.loads(out.stdout)


def probe(path):
    """Video properties via ffprobe, or None if ffprobe is unavailable.

    Streams are probed separately and parsed as key=value rather than
    positionally: ffprobe emits fields in its own order, not the order you
    request them, so both positional parsing and "read until codec_type"
    silently drop or transpose values.
    """
    if not shutil.which("ffprobe"):
        return None

    import os
    env = dict(os.environ)
    env["DYLD_FALLBACK_LIBRARY_PATH"] = \
        "/opt/homebrew/Cellar/x265/4.2/lib:/opt/homebrew/lib"

    def run(args):
        r = subprocess.run(["ffprobe", "-v", "error"] + args + [str(path)],
                           capture_output=True, text=True, env=env)
        return r.stdout if r.returncode == 0 else None

    video = run(["-select_streams", "v:0", "-show_entries",
                 "stream=codec_name,pix_fmt,width,height",
                 "-of", "default=noprint_wrappers=1"])
    if video is None:
        return None

    info = {}
    for line in video.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k] = v

    audio = run(["-select_streams", "a", "-show_entries",
                 "stream=codec_name", "-of", "csv=p=0"])
    info["has_audio"] = bool(audio and audio.strip())
    return info


def moov_at_front(path, window=4096):
    """True if the moov atom starts within the first `window` bytes.

    Pure stdlib, so this works even without ffmpeg installed.
    """
    try:
        with open(path, "rb") as f:
            pos = 0
            while True:
                head = f.read(8)
                if len(head) < 8:
                    return False
                size = struct.unpack(">I", head[:4])[0]
                typ = head[4:8]
                if typ == b"moov":
                    return pos < window
                if size == 1:                       # 64-bit extended size
                    size = struct.unpack(">Q", f.read(8))[0]
                if size == 0:
                    return False
                pos += size
                f.seek(pos)
    except OSError:
        return False


def main():
    print("config.js")
    cfg = load_config()
    if cfg is None:
        print(f"\nFAIL ({len(failures)} problem(s))")
        return 1

    clips = cfg.get("CLIPS") or []
    if not clips:
        fail("CLIPS is empty")
    else:
        ok(f"{len(clips)} clips")

    print("\nmapping")
    seen_codes, seen_keys = {}, {}
    for c in clips:
        key = c.get("key")
        if not key:
            fail(f"clip with no key: {c}")
            continue
        if key in seen_keys:
            fail(f"duplicate key {key!r}")
        seen_keys[key] = True

        code = c.get("barcode")
        if code is None:
            warn(f"{key}: no barcode — reachable only via the spiral switcher")
            continue
        if not isinstance(code, int) or isinstance(code, bool) \
           or not (0 <= code <= MAX_BARCODE):
            fail(f"{key}: barcode must be an integer 0-{MAX_BARCODE}, got {code!r}")
            continue
        if code in seen_codes:
            fail(f"barcode {code} used by both {seen_codes[code]!r} and {key!r} "
                 "— two markers would match the same printed square")
            continue
        seen_codes[code] = key

        marker = ROOT / "assets" / "marker" / "barcode" / f"barcode-{code}.png"
        if not marker.exists():
            fail(f"{key}: barcode {code} has no printable marker at "
                 f"{marker.relative_to(ROOT)} — run tools/make_barcode_markers.py")

    if seen_codes:
        ok("barcodes " + ", ".join(
            f"{c}->{k}" for c, k in sorted(seen_codes.items())))

    print("\nvideo files")
    total = 0
    for c in clips:
        key, src = c.get("key"), c.get("src")
        if not src:
            fail(f"{key}: no src")
            continue
        path = ROOT / src
        if not path.exists():
            fail(f"{key}: missing file {src}")
            continue
        mb = path.stat().st_size / 1048576
        total += mb

        if not moov_at_front(path):
            fail(f"{key}: moov atom is not at the front of {src} — the browser "
                 "must download nearly the whole file to read its dimensions. "
                 "Re-encode with tools/transcode.sh")

        info = probe(path)
        if info is None:
            warn(f"{key}: ffprobe unavailable, codec not checked")
        else:
            if info.get("pix_fmt") != "yuv420p":
                fail(f"{key}: pix_fmt is {info.get('pix_fmt')}, must be yuv420p "
                     "— iOS hardware decoders are 4:2:0 only")
            if info.get("codec_name") != "h264":
                warn(f"{key}: codec is {info.get('codec_name')}, expected h264")
            if info.get("has_audio"):
                warn(f"{key}: has an audio track; muted video is what lets iOS "
                     "autoplay into a texture")
        if mb > SIZE_WARN_MB:
            warn(f"{key}: {mb:.1f} MB is large for a poster clip")

    if not failures:
        ok(f"all {len(clips)} files present and poster-safe")
    print(f"\ntotal payload: {total:.1f} MB")

    print()
    if failures:
        print(f"FAIL — {len(failures)} problem(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS — {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
