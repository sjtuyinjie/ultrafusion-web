#!/usr/bin/env python3
"""Convert 3DGS PLY to .splat (32-byte rows) for GaussianSplats3D."""

from __future__ import annotations

import math
import struct
from pathlib import Path

import numpy as np

SH_C0 = 0.28209479177387814
ROW_SIZE = 32


def read_header(data: bytes) -> tuple[int, int, list[str]]:
    idx = data.find(b"end_header")
    if idx < 0:
        raise RuntimeError("Invalid PLY: end_header not found")
    end = idx + len(b"end_header")
    if data[end : end + 2] == b"\r\n":
        end += 2
    elif data[end : end + 1] in (b"\n", b"\r"):
        end += 1

    vertex_count = 0
    props: list[str] = []
    for line in data[:end].decode("ascii", errors="replace").splitlines():
        if line.startswith("element vertex "):
            vertex_count = int(line.split()[-1])
        elif line.startswith("property float "):
            props.append(line.split()[-1])
    return end, vertex_count, props


def dc_decode(value: float) -> float:
    return 0.5 + SH_C0 * value


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def clamp_u8(value: float) -> int:
    return int(max(0, min(255, round(value))))


def encode_quaternion_u8(w: float, x: float, y: float, z: float) -> tuple[int, int, int, int]:
    length = math.sqrt(w * w + x * x + y * y + z * z)
    if length > 0:
        w, x, y, z = w / length, x / length, y / length, z / length
    return (
        clamp_u8(w * 128.0 + 128.0),
        clamp_u8(x * 128.0 + 128.0),
        clamp_u8(y * 128.0 + 128.0),
        clamp_u8(z * 128.0 + 128.0),
    )


def convert(src: Path, dst: Path, min_alpha: int = 1) -> None:
    data = src.read_bytes()
    body_start, vertex_count, props = read_header(data)
    required = {
        "x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
        "rot_0", "rot_1", "rot_2", "rot_3", "scale_0", "scale_1", "scale_2",
    }
    if not required.issubset(props):
        raise RuntimeError(f"PLY missing required properties: {sorted(required - set(props))}")

    stride = len(props) * 4
    prop_index = {name: i for i, name in enumerate(props)}

    out = bytearray(vertex_count * ROW_SIZE)
    skipped = 0
    written = 0

    for vi in range(vertex_count):
        vals = struct.unpack_from("<" + "f" * len(props), data, body_start + vi * stride)
        x = vals[prop_index["x"]]
        y = vals[prop_index["y"]]
        z = vals[prop_index["z"]]
        if not all(math.isfinite(vals[prop_index[k]]) for k in ("x", "y", "z", "opacity", "rot_0", "rot_1", "rot_2", "rot_3", "scale_0", "scale_1", "scale_2", "f_dc_0", "f_dc_1", "f_dc_2")):
            skipped += 1
            continue

        scale_x = math.exp(vals[prop_index["scale_0"]])
        scale_y = math.exp(vals[prop_index["scale_1"]])
        scale_z = math.exp(vals[prop_index["scale_2"]])

        r = clamp_u8(dc_decode(vals[prop_index["f_dc_0"]]) * 255.0)
        g = clamp_u8(dc_decode(vals[prop_index["f_dc_1"]]) * 255.0)
        b = clamp_u8(dc_decode(vals[prop_index["f_dc_2"]]) * 255.0)
        a = clamp_u8(sigmoid(vals[prop_index["opacity"]]) * 255.0)
        if a < min_alpha:
            skipped += 1
            continue

        qw, qx, qy, qz = encode_quaternion_u8(
            vals[prop_index["rot_0"]],
            vals[prop_index["rot_1"]],
            vals[prop_index["rot_2"]],
            vals[prop_index["rot_3"]],
        )

        off = written * ROW_SIZE
        struct.pack_into("<3f", out, off + 0, x, y, z)
        struct.pack_into("<3f", out, off + 12, scale_x, scale_y, scale_z)
        struct.pack_into("<4B", out, off + 24, r, g, b, a)
        struct.pack_into("<4B", out, off + 28, qw, qx, qy, qz)
        written += 1

    dst.write_bytes(bytes(out[: written * ROW_SIZE]))
    print(f"wrote: {dst}")
    print(f"gaussians: {written}")
    print(f"skipped: {skipped}")
    print(f"size: {dst.stat().st_size} bytes ({dst.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert PLY to .splat with optional alpha filtering")
    parser.add_argument("--src", type=Path, default=None, help="Input PLY file")
    parser.add_argument("--dst", type=Path, default=None, help="Output .splat file")
    parser.add_argument("--min-alpha", type=int, default=1, help="Minimum alpha (0-255) to keep (default: 1)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    src = args.src or (root / "assets" / "hkisland03_uf_gs_1.ply")
    dst = args.dst or (root / "assets" / "hkisland03_2.splat")

    convert(src, dst, min_alpha=args.min_alpha)
