#!/usr/bin/env python3
"""
Convert a large LAZ to a downsampled .points.bin cache for web viewer.

This avoids laspy write crashes by only reading the LAZ and writing a compact binary cache.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

import laspy
import numpy as np

MAGIC = b"UFPC2"


def laz_to_points_bin_downsampled(
    src: Path,
    dst: Path,
    stride: int = 4,
    margin: float = 0.0,
) -> tuple[int, int, float]:
    """
    Read LAZ, optionally trim outliers and stride-decimate, then write UFPC2 points.bin.

    Returns (original_count, kept_count, output_mb).
    """
    print(f"Reading {src.name}...")
    las = laspy.read(src)
    n_orig = len(las.points)
    print(f"  Points: {n_orig:,}")

    # Positions
    xyz = np.column_stack((las.x, las.y, las.z)).astype(np.float64)

    # Colors (handle 16-bit -> 8-bit)
    colors_raw = np.column_stack((las.red, las.green, las.blue))
    if colors_raw.dtype != np.uint8:
        colors = (colors_raw / 256).astype(np.uint8)
    else:
        colors = colors_raw.astype(np.uint8, copy=False)

    # Filter non-finite
    finite = np.isfinite(xyz).all(axis=1)
    if not finite.all():
        print(f"  Dropping {(~finite).sum():,} non-finite points")
        xyz = xyz[finite]
        colors = colors[finite]

    # Optional margin trim (remove far outliers)
    if margin > 0:
        mins = xyz.min(axis=0)
        maxs = xyz.max(axis=0)
        ranges = maxs - mins
        trim = ranges * margin
        inside = (
            (xyz[:, 0] >= mins[0] + trim[0])
            & (xyz[:, 0] <= maxs[0] - trim[0])
            & (xyz[:, 1] >= mins[1] + trim[1])
            & (xyz[:, 1] <= maxs[1] - trim[1])
            & (xyz[:, 2] >= mins[2] + trim[2])
            & (xyz[:, 2] <= maxs[2] - trim[2])
        )
        removed = (~inside).sum()
        if removed:
            print(f"  Trimming {removed:,} outliers ({removed / len(xyz) * 100:.1f}%) at margin={margin}")
            xyz = xyz[inside]
            colors = colors[inside]

    # Stride decimation
    if stride > 1:
        xyz = xyz[::stride]
        colors = colors[::stride]
        print(f"  Stride={stride} -> {len(xyz):,} points kept")

    # Write UFPC2
    count = len(xyz)
    positions_f32 = xyz.astype("<f4")

    with dst.open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<I", count))
        f.write(positions_f32.tobytes())
        f.write(colors.tobytes())

    size_mb = dst.stat().st_size / 1024 / 1024
    print(f"Wrote {dst.name}: {count:,} points, {size_mb:.1f} MB")
    return n_orig, count, size_mb


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("src", type=Path, help="Input LAZ")
    p.add_argument("dst", type=Path, help="Output .points.bin")
    p.add_argument("--stride", type=int, default=4, help="Keep every Nth point")
    p.add_argument("--margin", type=float, default=0.0, help="Trim margin fraction (0 disables)")
    args = p.parse_args()

    laz_to_points_bin_downsampled(args.src, args.dst, stride=args.stride, margin=args.margin)


if __name__ == "__main__":
    main()