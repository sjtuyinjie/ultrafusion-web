#!/usr/bin/env python3
"""Decode SuperSplat packed PLY and export standard binary PLY + LAS + LAZ."""

from __future__ import annotations

import struct
from pathlib import Path

import laspy
import numpy as np

CHUNK_SIZE = 256
CHUNK_STRIDE = 18 * 4
VERTEX_STRIDE = 16


def read_header(data: bytes) -> tuple[int, dict[str, int]]:
    idx = data.find(b"end_header")
    if idx < 0:
        raise RuntimeError("Invalid PLY: end_header not found")
    end = idx + len(b"end_header")
    if data[end : end + 2] == b"\r\n":
        end += 2
    elif data[end : end + 1] in (b"\n", b"\r"):
        end += 1

    counts: dict[str, int] = {}
    for line in data[:end].decode("ascii", errors="replace").splitlines():
        if line.startswith("element "):
            parts = line.split()
            counts[parts[1]] = int(parts[2])
    return end, counts


def unpack_position(u: int) -> tuple[int, int, int]:
    xi = u & 0x7FF
    yi = (u >> 11) & 0x3FF
    zi = (u >> 21) & 0x7FF
    return xi, yi, zi


def decode_packed_color(packed_color: int, min_r: float, min_g: float, min_b: float, max_r: float, max_g: float, max_b: float) -> tuple[int, int, int]:
    # SuperSplat pack8888: R<<24 | G<<16 | B<<8 | A
    cr = (packed_color >> 24) & 0xFF
    cg = (packed_color >> 16) & 0xFF
    cb = (packed_color >> 8) & 0xFF

    color_r = min_r + (cr / 255.0) * (max_r - min_r)
    color_g = min_g + (cg / 255.0) * (max_g - min_g)
    color_b = min_b + (cb / 255.0) * (max_b - min_b)

    return (
        int(max(0, min(255, round(max(0.0, min(1.0, color_r)) * 255.0)))),
        int(max(0, min(255, round(max(0.0, min(1.0, color_g)) * 255.0)))),
        int(max(0, min(255, round(max(0.0, min(1.0, color_b)) * 255.0)))),
    )


def convert(src: Path, dst_ply: Path, dst_las: Path, dst_laz: Path) -> None:
    data = src.read_bytes()
    body_start, counts = read_header(data)
    chunk_count = counts["chunk"]
    vertex_count = counts["vertex"]

    chunk_start = body_start
    vertex_start = chunk_start + chunk_count * CHUNK_STRIDE

    xs = np.empty(vertex_count, dtype=np.float32)
    ys = np.empty(vertex_count, dtype=np.float32)
    zs = np.empty(vertex_count, dtype=np.float32)
    rs = np.empty(vertex_count, dtype=np.uint8)
    gs = np.empty(vertex_count, dtype=np.uint8)
    bs = np.empty(vertex_count, dtype=np.uint8)

    for vi in range(vertex_count):
        ci = min(vi // CHUNK_SIZE, chunk_count - 1)
        c_off = chunk_start + ci * CHUNK_STRIDE
        v_off = vertex_start + vi * VERTEX_STRIDE

        vals = struct.unpack_from("<18f", data, c_off)
        min_x, min_y, min_z, max_x, max_y, max_z = vals[0:6]
        min_r, min_g, min_b, max_r, max_g, max_b = vals[12:18]

        packed_pos, _, _, packed_color = struct.unpack_from("<4I", data, v_off)
        xi, yi, zi = unpack_position(packed_pos)

        xs[vi] = min_x + (xi / 2047.0) * (max_x - min_x)
        ys[vi] = min_y + (yi / 1023.0) * (max_y - min_y)
        zs[vi] = min_z + (zi / 2047.0) * (max_z - min_z)

        r, g, b = decode_packed_color(packed_color, min_r, min_g, min_b, max_r, max_g, max_b)
        rs[vi], gs[vi], bs[vi] = r, g, b

    with dst_ply.open("wb") as f:
        header = (
            "ply\n"
            "format binary_little_endian 1.0\n"
            "comment decoded from SuperSplat packed PLY (fixed RGBA color packing)\n"
            f"element vertex {vertex_count}\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "property uchar red\n"
            "property uchar green\n"
            "property uchar blue\n"
            "end_header\n"
        )
        f.write(header.encode("ascii"))
        for i in range(vertex_count):
            f.write(struct.pack("<fffBBB", float(xs[i]), float(ys[i]), float(zs[i]), int(rs[i]), int(gs[i]), int(bs[i])))

    hdr = laspy.LasHeader(point_format=3, version="1.2")
    hdr.scales = np.array([0.001, 0.001, 0.001], dtype=np.float64)
    hdr.offsets = np.array([float(xs.min()), float(ys.min()), float(zs.min())], dtype=np.float64)

    las = laspy.LasData(hdr)
    las.x = xs.astype(np.float64)
    las.y = ys.astype(np.float64)
    las.z = zs.astype(np.float64)
    las.red = (rs.astype(np.uint16) * 257)
    las.green = (gs.astype(np.uint16) * 257)
    las.blue = (bs.astype(np.uint16) * 257)
    las.write(dst_las)

    with laspy.open(dst_las) as reader:
        with laspy.open(dst_laz, mode="w", header=reader.header) as writer:
            for points in reader.chunk_iterator(500_000):
                writer.write_points(points)

    print(f"wrote ply: {dst_ply}")
    print(f"wrote las: {dst_las}")
    print(f"wrote laz: {dst_laz}")
    print(f"points: {vertex_count}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    assets = root / "assets"
    convert(
        assets / "hkisland03_uf_gs.ply",
        assets / "hkisland03_uf_gs_standard_binary.ply",
        assets / "hkisland03_uf_gs_standard_binary.las",
        assets / "hkisland03_uf_gs_standard_binary.laz",
    )
