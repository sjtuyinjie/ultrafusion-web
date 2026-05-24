#!/usr/bin/env python3
"""
Downsample a LAZ file by removing outliers and decimating points.

Target: reduce file size to < 100MB while preserving visual quality.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import laspy
import numpy as np


def downsample_laz(
    src: Path,
    dst: Path,
    stride: int = 4,
    margin: float = 0.02,
    remove_outliers: bool = True,
) -> tuple[int, int, float]:
    """
    Downsample LAZ file.

    Args:
        src: Input LAZ file
        dst: Output LAZ file
        stride: Keep every N-th point (e.g., 4 means keep 25%)
        margin: Percentage of bounding box to trim from each side (0.02 = 2%)
        remove_outliers: If True, trim points outside the central region

    Returns:
        (original_count, kept_count, output_size_mb)
    """
    print(f"Reading {src}...")
    las = laspy.read(src)
    xyz = np.column_stack((las.x, las.y, las.z)).astype(np.float64)
    n_orig = len(xyz)
    print(f"  Original points: {n_orig:,}")

    # Step 1: Remove NaN/Inf (should be none, but just in case)
    finite_mask = np.isfinite(xyz).all(axis=1)
    if not finite_mask.all():
        print(f"  Removing {(~finite_mask).sum():,} non-finite points")
        xyz = xyz[finite_mask]
        # We need to also filter the las points
        las.points = las.points[finite_mask]

    # Step 2: Optional outlier removal via bounding box trimming
    if remove_outliers and margin > 0:
        mins = xyz.min(axis=0)
        maxs = xyz.max(axis=0)
        ranges = maxs - mins
        trim = ranges * margin

        keep_mask = (
            (xyz[:, 0] >= mins[0] + trim[0])
            & (xyz[:, 0] <= maxs[0] - trim[0])
            & (xyz[:, 1] >= mins[1] + trim[1])
            & (xyz[:, 1] <= maxs[1] - trim[1])
            & (xyz[:, 2] >= mins[2] + trim[2])
            & (xyz[:, 2] <= maxs[2] - trim[2])
        )
        removed = (~keep_mask).sum()
        if removed > 0:
            print(f"  Trimming {removed:,} outlier points ({removed / n_orig * 100:.1f}%) at {margin*100:.1f}% margin")
            xyz = xyz[keep_mask]
            las.points = las.points[keep_mask]

    # Step 3: Stride-based decimation
    n_before_stride = len(las.points)
    if stride > 1:
        keep_idx = np.arange(0, n_before_stride, stride)
        las.points = las.points[keep_idx]
        print(f"  Decimated with stride={stride}: {n_before_stride:,} -> {len(las.points):,} points")

    # Write output
    print(f"Writing {dst}...")
    las.write(dst)

    size_mb = dst.stat().st_size / 1024 / 1024
    print(f"Done: {len(las.points):,} points, {size_mb:.1f} MB")

    return n_orig, len(las.points), size_mb


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path, help="Input LAZ file")
    parser.add_argument("dst", type=Path, help="Output LAZ file")
    parser.add_argument("--stride", type=int, default=4, help="Keep every N-th point (default: 4)")
    parser.add_argument("--margin", type=float, default=0.02, help="Trim margin as fraction of bbox (default: 0.02)")
    parser.add_argument("--no-trim", action="store_true", help="Disable outlier trimming")
    args = parser.parse_args()

    downsample_laz(
        args.src,
        args.dst,
        stride=args.stride,
        margin=0.0 if args.no_trim else args.margin,
        remove_outliers=not args.no_trim,
    )


if __name__ == "__main__":
    main()