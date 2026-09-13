#!/usr/bin/env python3
"""Generate the printable 3x3_hamming_6_3 barcode markers.

Barcode (matrix-code) markers carry a small number in a 3x3 grid instead of an
image pattern, so unlike the spiral marker they need no .patt descriptor at
all -- AR.js decodes the grid directly. That makes them the right tool for
"this figure plays that movie": one marker per clip, no pattern matching.

Why generate rather than download:

  * The widely-linked collection at nicolocarpignoli/artoolkit-barcode-markers-
    collection declares no licence at all, so redistributing its PNGs in a
    public repo is murky for no benefit.
  * The encoding is mechanical, not creative. Cells 0, 6 and 8 are fixed
    orientation cells (0, 0, 1); the other six carry 5 data bits plus parity.
  * Those PNGs have no white quiet zone (they are black to the corners), which
    invites cropping the marker flush and breaking detection. Generating lets
    us bake the quiet zone in, matching spiro-marker.png.

TABLE below is the ground truth, decoded from the canonical images and pinned
by tests/test_barcode_table.py. Geometry is shared with make_marker.py so both
marker families print at the same scale and share one patternRatio: with
TOTAL=1200 the inner region is 450px and each cell is exactly 150px, so there
are no fractional cell boundaries to round.
"""

from pathlib import Path

from make_marker import (  # geometry + PNG writer, deliberately shared
    BLACK,
    BORDER,
    INNER,
    INNER_ORIGIN,
    QUIET,
    TOTAL,
    write_png,
)

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "marker" / "barcode"

CELL = INNER // 3  # 150px, exact

# 3x3_hamming_6_3: 8 ids, minimum pairwise cell distance 3.
# Row-major, '1' = white cell.
TABLE = {
    0: "011111011",
    1: "011100001",
    2: "010011001",
    3: "010000011",
    4: "001010011",
    5: "001001001",
    6: "000110001",
    7: "000101011",
}

FIXED_CELLS = {0: "0", 6: "0", 8: "1"}  # orientation cells, constant across ids


def compose(bits: str) -> list[bytearray]:
    """White quiet zone, black border, then the 3x3 grid in the inner region."""
    rows = []
    for y in range(TOTAL):
        row = bytearray()
        in_black = QUIET <= y < TOTAL - QUIET
        gy = (y - INNER_ORIGIN) // CELL
        in_inner_y = 0 <= y - INNER_ORIGIN < INNER
        for x in range(TOTAL):
            gx = (x - INNER_ORIGIN) // CELL
            if in_inner_y and 0 <= x - INNER_ORIGIN < INNER:
                v = 255 if bits[gy * 3 + gx] == "1" else 0
            elif in_black and QUIET <= x < TOTAL - QUIET:
                v = 0
            else:
                v = 255
            row += bytes((v, v, v))
        rows.append(row)
    return rows


def sample_grid(rows: list[bytearray]) -> str:
    """Read the 3x3 grid back out of composed pixels, at cell centres."""
    out = ""
    for gy in range(3):
        for gx in range(3):
            cx = INNER_ORIGIN + gx * CELL + CELL // 2
            cy = INNER_ORIGIN + gy * CELL + CELL // 2
            out += "1" if rows[cy][cx * 3] > 128 else "0"
    return out


def distance(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b))


def self_check(composed: dict[int, list[bytearray]]) -> None:
    """Fail loudly rather than print a marker that decodes to the wrong id.

    A wrong bit layout is worse than one that fails to decode: it resolves to a
    different *valid* id, so the poster silently plays the wrong movie.
    """
    assert len(set(TABLE.values())) == len(TABLE), "duplicate patterns in TABLE"

    for mid, bits in TABLE.items():
        for cell, expected in FIXED_CELLS.items():
            assert bits[cell] == expected, (
                f"id {mid}: orientation cell {cell} is {bits[cell]}, expected {expected}"
            )

    pairs = [
        (a, b, distance(TABLE[a], TABLE[b]))
        for a in sorted(TABLE)
        for b in sorted(TABLE)
        if a < b
    ]
    worst = min(p[2] for p in pairs)
    print(f"  minimum pairwise cell distance: {worst} (family guarantees 3)")
    assert worst >= 3, f"distance {worst} too low; wrong table for hamming_6_3?"

    for mid, bits in TABLE.items():
        got = sample_grid(composed[mid])
        assert got == bits, f"id {mid}: composed pixels decode to {got}, expected {bits}"
    print(f"  all {len(TABLE)} rendered markers decode back to their table entry")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(
        f"geometry: {TOTAL}px total, {QUIET}px quiet zone, {BLACK}px black square, "
        f"{BORDER}px border, {INNER}px inner, {CELL}px cell"
    )
    print("rendering...")
    composed = {mid: compose(bits) for mid, bits in TABLE.items()}

    print("self-checking...")
    self_check(composed)

    for mid in sorted(composed):
        path = OUT_DIR / f"barcode-{mid}.png"
        write_png(path, TOTAL, TOTAL, composed[mid])
        print(f"  wrote {path.name}  bits={TABLE[mid]}")

    print(f"\n{len(composed)} markers in {OUT_DIR}")


if __name__ == "__main__":
    main()
