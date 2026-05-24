#!/usr/bin/env python3
"""Decode a LAZ/LAS file into a compact web cache (UFPC2 points.bin)."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

import laspy
import numpy as np

MAGIC = b"UFPC2"


def export_laz_to_points_bin(src: Path, dst: Path) -> int:
    las = laspy.read(src)
    count = len(las.points)

    positions = np.column_stack((las.x, las.y, las.z)).astype("<f4", copy=False)
    colors = np.column_stack(
        (
            np.asarray(las.red, dtype=np.uint16 if las.point_format.id >= 2 else np.uint8),
            np.asarray(las.green, dtype=np.uint16 if las.point_format.id >= 2 else np.uint8),
            np.asarray(las.blue, dtype=np.uint16 if las.point_format.id >= 2 else np.uint8),
        )
    )
    if colors.dtype != np.uint8:
        colors = (colors / 256).astype(np.uint8)
    else:
        colors = colors.astype(np.uint8, copy=False)

    with dst.open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<I", count))
        f.write(positions.tobytes())
        f.write(colors.tobytes())

    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "src",
        type=Path,
        nargs="?",
        default=Path("assets/hkisland03_uf_gs_1.laz"),
    )
    parser.add_argument(
        "dst",
        type=Path,
        nargs="?",
        default=Path("assets/hkisland03_uf_gs_1.points.bin"),
    )
    args = parser.parse_args()
    count = export_laz_to_points_bin(args.src, args.dst)
    print(f"Wrote {count:,} points to {args.dst} ({args.dst.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
