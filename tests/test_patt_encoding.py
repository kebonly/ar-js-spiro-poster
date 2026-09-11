#!/usr/bin/env python3
"""Check our .patt rotation convention against AR.js's own reference marker.

This exists because getting it wrong is nearly invisible in testing: the
marker still gets detected, but the tracker reports the wrong rotation when
the marker is held at 90 or 270 degrees, so the video appears upside down.
A poster on a wall is always upright, so the bug would very plausibly survive
all local testing and only show up when somebody tilts their phone.

patt.hiro stores the same 16x16 pattern four times, once per rotation. So if
our rotate() matches AR.js's, feeding it the reference's first block must
reproduce all four reference blocks exactly.

Run:  python3 tests/test_patt_encoding.py
Needs network on first run to fetch patt.hiro (cached next to this file).
"""

import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

from make_marker import rotate  # noqa: E402

REFERENCE_URL = (
    "https://raw.githubusercontent.com/AR-js-org/AR.js/master/data/data/patt.hiro"
)
CACHE = HERE / "patt.hiro"


def load_reference() -> list[list[list[list[int]]]]:
    if not CACHE.exists():
        print(f"fetching {REFERENCE_URL}")
        urllib.request.urlretrieve(REFERENCE_URL, CACHE)

    values = [int(t) for t in CACHE.read_text().split()]
    expected = 4 * 3 * 16 * 16
    assert len(values) == expected, f"expected {expected} values, got {len(values)}"

    blocks = []
    i = 0
    for _orientation in range(4):
        channels = []
        for _channel in range(3):
            channels.append([values[i + r * 16 : i + (r + 1) * 16] for r in range(16)])
            i += 256
        blocks.append(channels)
    return blocks


def main() -> int:
    reference = load_reference()
    base = reference[0][0]

    failures = []
    for orientation in range(4):
        ours = rotate(base, orientation)
        theirs = reference[orientation][0]
        if ours == theirs:
            print(f"  {orientation * 90:3d} deg: match")
        else:
            mean = sum(
                abs(ours[y][x] - theirs[y][x]) for y in range(16) for x in range(16)
            ) / 256
            print(f"  {orientation * 90:3d} deg: MISMATCH (mean abs diff {mean:.1f})")
            failures.append(orientation * 90)

    if failures:
        print(f"\nFAIL: rotation convention differs from AR.js at {failures}")
        return 1

    print("\nPASS: rotation convention matches AR.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
