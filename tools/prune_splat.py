#!/usr/bin/env python3
"""Prune a .splat file by removing splats with alpha below a threshold.

This is useful to bring a .splat just under GitHub's 100MB hard limit
while removing as few points as possible (only the most transparent edge splats).
"""

from __future__ import annotations

import argparse
from pathlib import Path


ROW_SIZE = 32          # 3f pos + 3f scale + 4B color + 4B quat
ALPHA_OFFSET = 27      # byte index of alpha within each 32-byte row


def prune_splat(src: Path, dst: Path, min_alpha: int = 1) -> int:
    data = src.read_bytes()
    if len(data) % ROW_SIZE != 0:
        raise RuntimeError(f"File size {len(data)} is not a multiple of {ROW_SIZE}")

    total = len(data) // ROW_SIZE
    kept_rows = bytearray()

    for i in range(total):
        row = data[i * ROW_SIZE : (i + 1) * ROW_SIZE]
        alpha = row[ALPHA_OFFSET]
        if alpha >= min_alpha:
            kept_rows.extend(row)

    dst.write_bytes(kept_rows)
    kept = len(kept_rows) // ROW_SIZE
    removed = total - kept
    return kept, removed, total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path, help="Input .splat file")
    parser.add_argument("dst", type=Path, nargs="?", help="Output .splat file (default: overwrite src)")
    parser.add_argument("--min-alpha", type=int, default=1,
                        help="Minimum alpha value (0-255) to keep. Default 1 removes only fully transparent splats.")
    args = parser.parse_args()

    src = args.src
    dst = args.dst or src

    kept, removed, total = prune_splat(src, dst, min_alpha=args.min_alpha)

    new_size = dst.stat().st_size
    print(f"Input : {src} ({src.stat().st_size / 1024 / 1024:.2f} MB, {total:,} splats)")
    print(f"Output: {dst} ({new_size / 1024 / 1024:.2f} MB, {kept:,} splats)")
    print(f"Removed {removed:,} splats ({removed / total * 100:.2f}%) with alpha < {args.min_alpha}")
    print(f"New size: {new_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()