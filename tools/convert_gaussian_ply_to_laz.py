#!/usr/bin/env python3
"""Convert standard 3DGS PLY (x,y,z,f_dc_*) to LAS/LAZ point cloud."""

from __future__ import annotations

import math
import struct
from pathlib import Path

import laspy
import numpy as np

SH_C0 = 0.28209479177387814


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


def linear_to_uint8(value: float) -> int:
    return int(max(0, min(255, round(max(0.0, min(1.0, value)) * 255.0))))


def convert(src: Path, dst_las: Path, dst_laz: Path) -> None:
    data = src.read_bytes()
    body_start, vertex_count, props = read_header(data)

    required = {"x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2"}
    if not required.issubset(props):
        raise RuntimeError(f"PLY missing required properties: {sorted(required - set(props))}")

    stride = len(props) * 4
    prop_index = {name: i for i, name in enumerate(props)}

    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    rs: list[int] = []
    gs: list[int] = []
    bs: list[int] = []

    ix = prop_index["x"]
    iy = prop_index["y"]
    iz = prop_index["z"]
    ir = prop_index["f_dc_0"]
    ig = prop_index["f_dc_1"]
    ib = prop_index["f_dc_2"]

    skipped = 0
    for vi in range(vertex_count):
        vals = struct.unpack_from("<" + "f" * len(props), data, body_start + vi * stride)
        x, y, z = vals[ix], vals[iy], vals[iz]
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
            skipped += 1
            continue

        xs.append(x)
        ys.append(y)
        zs.append(z)
        rs.append(linear_to_uint8(dc_decode(vals[ir])))
        gs.append(linear_to_uint8(dc_decode(vals[ig])))
        bs.append(linear_to_uint8(dc_decode(vals[ib])))

    if not xs:
        raise RuntimeError("No valid points after filtering NaN/Inf coordinates.")

    x_arr = np.asarray(xs, dtype=np.float64)
    y_arr = np.asarray(ys, dtype=np.float64)
    z_arr = np.asarray(zs, dtype=np.float64)
    r_arr = np.asarray(rs, dtype=np.uint16)
    g_arr = np.asarray(gs, dtype=np.uint16)
    b_arr = np.asarray(bs, dtype=np.uint16)

    hdr = laspy.LasHeader(point_format=3, version="1.2")
    hdr.scales = np.array([0.001, 0.001, 0.001], dtype=np.float64)
    hdr.offsets = np.array([float(x_arr.min()), float(y_arr.min()), float(z_arr.min())], dtype=np.float64)

    las = laspy.LasData(hdr)
    las.x = x_arr
    las.y = y_arr
    las.z = z_arr
    las.red = r_arr * 257
    las.green = g_arr * 257
    las.blue = b_arr * 257
    las.write(dst_las)

    with laspy.open(dst_las) as reader:
        with laspy.open(dst_laz, mode="w", header=reader.header) as writer:
            for points in reader.chunk_iterator(500_000):
                writer.write_points(points)

    print(f"source: {src}")
    print(f"wrote las: {dst_las}")
    print(f"wrote laz: {dst_laz}")
    print(f"valid points: {len(xs)}")
    print(f"skipped invalid xyz: {skipped}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    assets = root / "assets"
    convert(
        assets / "hkisland03_uf_gs_1.ply",
        assets / "hkisland03_uf_gs_1.las",
        assets / "hkisland03_uf_gs_1.laz",
    )
