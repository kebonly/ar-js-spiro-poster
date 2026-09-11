#!/usr/bin/env python3
"""Generate the printable AR marker and its ARToolKit .patt descriptor.

Pure stdlib (no PIL/numpy) so it runs anywhere with python3.

Marker geometry follows the ARToolKit convention that AR.js defaults to
(patternRatio 0.5):

    +-----------------------------+   <- white quiet zone (required for
    |   #########################   |     detection; do not crop it away)
    |   #                       #   |
    |   #      +---------+      #   |  <- black border, 1/4 of the black
    |   #      | pattern |      #   |     square's width on each side
    |   #      +---------+      #   |
    |   #                       #   |  <- inner pattern, 1/2 of the black
    |   #########################   |     square's width. Only this region
    +-----------------------------+       is encoded into the .patt file.

The pattern itself is a 1.5-turn Archimedean spiral plus a solid corner block.
Two constraints drive that design: the .patt is only 16x16, so fine detail is
destroyed; and the pattern must not be close to rotationally symmetric, or the
tracker will flip the model's orientation between frames. The corner block is
what guarantees the second property -- the script asserts it below.
"""

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "marker"

# --- geometry (pixels in the printable PNG) --------------------------------
TOTAL = 1200
QUIET = 150                     # white margin outside the black square
BLACK = TOTAL - 2 * QUIET       # 900
BORDER = BLACK // 4             # 225  -> inner is half the black square
INNER = BLACK - 2 * BORDER      # 450
INNER_ORIGIN = QUIET + BORDER

SUPERSAMPLE = 2

# --- pattern shape (normalised to the inner square, centred on 0) ----------
TURNS = 1.5
THETA_MAX = TURNS * 2 * math.pi
R_MAX = 0.42
SPIRAL_A = R_MAX / THETA_MAX
STROKE_HALF = 0.065             # stroke width 0.13 -> ~2px at 16x16

BLOCK_SIZE = 0.17               # solid square that breaks rotational symmetry
BLOCK_INSET = 0.025


def coverage(nx: float, ny: float) -> float:
    """Ink coverage at normalised point (nx, ny), both in [-0.5, 0.5]."""
    # Solid corner block, anchored top-left.
    bx0 = -0.5 + BLOCK_INSET
    by0 = -0.5 + BLOCK_INSET
    if bx0 <= nx <= bx0 + BLOCK_SIZE and by0 <= ny <= by0 + BLOCK_SIZE:
        return 1.0

    r = math.hypot(nx, ny)
    if r > R_MAX + STROKE_HALF:
        return 0.0

    theta_p = math.atan2(ny, nx) % (2 * math.pi)
    best = float("inf")
    k = 0
    while True:
        theta = theta_p + 2 * math.pi * k
        if theta > THETA_MAX:
            break
        best = min(best, abs(r - SPIRAL_A * theta))
        k += 1

    return 1.0 if best <= STROKE_HALF else 0.0


def render_inner() -> list[list[int]]:
    """Render the inner pattern as INNER x INNER greyscale (0=black, 255=white)."""
    ss = SUPERSAMPLE
    inv = 1.0 / (INNER * ss)
    rows = []
    for y in range(INNER):
        row = []
        for x in range(INNER):
            acc = 0.0
            for sy in range(ss):
                ny = (y * ss + sy + 0.5) * inv - 0.5
                for sx in range(ss):
                    nx = (x * ss + sx + 0.5) * inv - 0.5
                    acc += coverage(nx, ny)
            ink = acc / (ss * ss)
            row.append(int(round(255 * (1.0 - ink))))
        rows.append(row)
    return rows


def compose_marker(inner: list[list[int]]) -> list[bytearray]:
    """Place the inner pattern inside the black border and white quiet zone."""
    rows = []
    for y in range(TOTAL):
        row = bytearray()
        in_black = QUIET <= y < TOTAL - QUIET
        iy = y - INNER_ORIGIN
        in_inner_y = 0 <= iy < INNER
        for x in range(TOTAL):
            ix = x - INNER_ORIGIN
            if in_inner_y and 0 <= ix < INNER:
                v = inner[iy][ix]
            elif in_black and QUIET <= x < TOTAL - QUIET:
                v = 0
            else:
                v = 255
            row += bytes((v, v, v))
        rows.append(row)
    return rows


def write_png(path: Path, width: int, height: int, rgb_rows: list[bytearray]) -> None:
    raw = b"".join(b"\x00" + bytes(r) for r in rgb_rows)

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def downsample_16(inner: list[list[int]]) -> list[list[int]]:
    """Box-average the inner pattern down to the 16x16 grid the .patt uses."""
    cell = INNER / 16.0
    grid = []
    for gy in range(16):
        row = []
        y0, y1 = int(gy * cell), int((gy + 1) * cell)
        for gx in range(16):
            x0, x1 = int(gx * cell), int((gx + 1) * cell)
            total = 0
            count = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    total += inner[y][x]
                    count += 1
            row.append(total // count)
        grid.append(row)
    return grid


def rotate(grid: list[list[int]], orientation: int) -> list[list[int]]:
    """Sample the grid the way AR.js's pattern encoder does for each rotation.

    The handedness here is not a free choice -- it has to match AR.js exactly,
    or the marker is still detected but reports the wrong rotation when held at
    90 or 270 degrees. Verified against AR.js's own patt.hiro by
    tests/test_patt_encoding.py, which reconstructs all four reference blocks
    using this function.
    """
    out = []
    for y in range(16):
        row = []
        for x in range(16):
            if orientation == 0:
                dx, dy = x, y
            elif orientation == 1:
                dx, dy = 15 - y, x
            elif orientation == 2:
                dx, dy = 15 - x, 15 - y
            else:
                dx, dy = y, 15 - x
            row.append(grid[dy][dx])
        out.append(row)
    return out


def write_patt(path: Path, grid: list[list[int]]) -> None:
    """Emit the ARToolKit pattern file: 4 orientations x 3 channels x 16 rows.

    Channels run B, G, R. Our pattern is greyscale so all three are identical,
    but the ordering is kept faithful to the format.
    """
    out = []
    for orientation in range(4):
        if orientation:
            out.append("")
        rot = rotate(grid, orientation)
        for _channel in range(3):
            for row in rot:
                out.append("".join(f"{v:4d}" for v in row))
    path.write_text("\n".join(out) + "\n")


def check_asymmetry(grid: list[list[int]]) -> None:
    """Fail loudly if the pattern is close to rotationally symmetric."""
    base = rotate(grid, 0)
    print("\n16x16 as the tracker sees it (each rotation must look distinct):")
    for orientation in range(4):
        rot = rotate(grid, orientation)
        art = "\n".join(
            "".join(" .:-=+*#%@"[min(9, (255 - v) * 10 // 256)] for v in row)
            for row in rot
        )
        print(f"\n  rotation {orientation * 90}deg")
        for line in art.splitlines():
            print("    " + line)

    print()
    for orientation in (1, 2, 3):
        rot = rotate(grid, orientation)
        diff = sum(
            abs(base[y][x] - rot[y][x]) for y in range(16) for x in range(16)
        ) / (256 * 255)
        status = "OK" if diff > 0.08 else "TOO SYMMETRIC"
        print(f"  mean difference vs {orientation * 90}deg rotation: {diff:.3f}  {status}")
        assert diff > 0.08, (
            f"pattern is too close to symmetric under {orientation * 90}deg "
            "rotation; the tracker would flip orientation between frames"
        )

    contrast = sum(1 for row in grid for v in row if v < 128) / 256.0
    print(f"  ink coverage: {contrast:.1%} (healthy range is roughly 20-50%)")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("rendering pattern...")
    inner = render_inner()

    print("writing printable marker...")
    write_png(OUT_DIR / "spiro-marker.png", TOTAL, TOTAL, compose_marker(inner))

    print("writing pattern descriptor...")
    grid = downsample_16(inner)
    write_patt(OUT_DIR / "spiro.patt", grid)

    check_asymmetry(grid)

    print(f"\nwrote {OUT_DIR / 'spiro-marker.png'}")
    print(f"wrote {OUT_DIR / 'spiro.patt'}")


if __name__ == "__main__":
    main()
