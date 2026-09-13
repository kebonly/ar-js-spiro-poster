#!/usr/bin/env python3
"""Pin our barcode bit table against the canonical 3x3_hamming_6_3 markers.

tools/make_barcode_markers.py generates the markers from a hard-coded TABLE
rather than shipping someone else's unlicensed PNGs. That is only safe if the
table is right, and the failure mode if it isn't is nasty: a wrong bit layout
produces a marker that decodes to a *different valid id*, so the poster plays
the wrong movie with no error anywhere.

So this fetches the canonical images, decodes their 3x3 grids, and asserts our
table matches exactly. Same role as tests/test_patt_encoding.py.

Run:  python3 tests/test_barcode_table.py
Needs network on first run (images are cached next to this file).
"""

import struct
import sys
import urllib.request
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

from make_barcode_markers import FIXED_CELLS, TABLE, distance  # noqa: E402

BASE = (
    "https://raw.githubusercontent.com/nicolocarpignoli/"
    "artoolkit-barcode-markers-collection/master/3x3_hamming_6_3"
)
CACHE = HERE / "barcode-reference"


def decode_png(data: bytes):
    """Minimal PNG reader: 8-bit truecolour, all five filter types."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    i, idat, ihdr = 8, b"", None
    while i < len(data):
        length = struct.unpack(">I", data[i : i + 4])[0]
        typ = data[i + 4 : i + 8]
        body = data[i + 8 : i + 8 + length]
        if typ == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif typ == b"IDAT":
            idat += body
        i += 12 + length

    width, height, depth, colour = ihdr[0], ihdr[1], ihdr[2], ihdr[3]
    assert depth == 8 and colour == 2, f"expected 8-bit RGB, got depth={depth} colour={colour}"

    raw = zlib.decompress(idat)
    ch, stride = 3, width * 3
    prev = bytearray(stride)
    rows, p = [], 0
    for _y in range(height):
        f = raw[p]
        p += 1
        line = bytearray(raw[p : p + stride])
        p += stride
        for x in range(stride):
            a = line[x - ch] if x >= ch else 0
            b = prev[x]
            c = prev[x - ch] if x >= ch else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        rows.append(bytes(line))
        prev = line
    return width, height, rows


def grid_of(width: int, rows) -> str:
    """Sample the 3x3 grid at cell centres.

    The canonical images are 944px, so the inner region is 472px and a cell is
    157.33px -- deliberately float, because integer truncation drifts the last
    column onto a boundary seam.
    """
    origin = width / 4.0
    cell = (width / 2.0) / 3.0
    out = ""
    for gy in range(3):
        for gx in range(3):
            cx = int(origin + (gx + 0.5) * cell)
            cy = int(origin + (gy + 0.5) * cell)
            out += "1" if rows[cy][cx * 3] > 128 else "0"
    return out


def reference(mid: int) -> bytes:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{mid}.png"
    if not path.exists():
        url = f"{BASE}/{mid}.png"
        print(f"  fetching {url}")
        urllib.request.urlretrieve(url, path)
    return path.read_bytes()


def main() -> int:
    failures = []

    for mid in sorted(TABLE):
        width, _height, rows = decode_png(reference(mid))
        theirs = grid_of(width, rows)
        ours = TABLE[mid]
        if ours == theirs:
            print(f"  id {mid}: {ours}  match")
        else:
            print(f"  id {mid}: ours={ours} canonical={theirs}  MISMATCH")
            failures.append(mid)

    # Independent of the reference: the properties the family is chosen for.
    worst = min(
        distance(TABLE[a], TABLE[b])
        for a in sorted(TABLE)
        for b in sorted(TABLE)
        if a < b
    )
    print(f"\n  minimum pairwise cell distance: {worst}")
    if worst < 3:
        print("  FAIL: hamming_6_3 must guarantee at least 3")
        failures.append("distance")

    for cell, expected in FIXED_CELLS.items():
        if any(TABLE[m][cell] != expected for m in TABLE):
            print(f"  FAIL: orientation cell {cell} is not constant {expected}")
            failures.append(f"cell{cell}")

    if failures:
        print(f"\nFAIL: {failures}")
        return 1
    print(f"\nPASS: {len(TABLE)} barcode patterns match the canonical markers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
