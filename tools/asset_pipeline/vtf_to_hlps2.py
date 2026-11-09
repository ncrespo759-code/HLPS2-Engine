#!/usr/bin/env python3
"""Convert a conservative subset of Valve VTF textures to HLPS2 RGBA5551.

Supported VTF versions: 7.0-7.2, one frame, one 2D image, no cubemap.
Supported image formats: RGBA8888, ABGR8888, RGB888, BGR888, BGRA8888,
and DXT1. Output is a little-endian H2TX container with linear PSMCT16
(RGBA5551) pixels. The PS2 runtime still needs to upload the payload to GS.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

FMT_RGBA8888 = 0
FMT_ABGR8888 = 1
FMT_RGB888 = 2
FMT_BGR888 = 3
FMT_DXT1 = 13
FMT_BGRA8888 = 12
VTF_ENVMAP = 0x00004000


def image_size(fmt: int, width: int, height: int) -> int:
    if fmt in (FMT_RGBA8888, FMT_ABGR8888, FMT_BGRA8888):
        return width * height * 4
    if fmt in (FMT_RGB888, FMT_BGR888):
        return width * height * 3
    if fmt == FMT_DXT1:
        return max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 8
    raise ValueError(f"unsupported VTF image format {fmt}")


def rgb565(value: int) -> tuple[int, int, int]:
    r = (value >> 11) & 31
    g = (value >> 5) & 63
    b = value & 31
    return (r * 255 // 31, g * 255 // 63, b * 255 // 31)


def decode_dxt1(data: bytes, width: int, height: int) -> bytes:
    out = bytearray(width * height * 4)
    blocks_x = max(1, (width + 3) // 4)
    blocks_y = max(1, (height + 3) // 4)
    expected = blocks_x * blocks_y * 8
    if len(data) < expected:
        raise ValueError("truncated DXT1 image data")

    pos = 0
    for by in range(blocks_y):
        for bx in range(blocks_x):
            c0, c1, bits = struct.unpack_from("<HHI", data, pos)
            pos += 8
            p0 = rgb565(c0)
            p1 = rgb565(c1)
            if c0 > c1:
                colors = [
                    (*p0, 255), (*p1, 255),
                    tuple((2 * p0[i] + p1[i]) // 3 for i in range(3)) + (255,),
                    tuple((p0[i] + 2 * p1[i]) // 3 for i in range(3)) + (255,),
                ]
            else:
                colors = [
                    (*p0, 255), (*p1, 255),
                    tuple((p0[i] + p1[i]) // 2 for i in range(3)) + (255,),
                    (0, 0, 0, 0),
                ]
            for py in range(4):
                for px in range(4):
                    x, y = bx * 4 + px, by * 4 + py
                    index = (bits >> (2 * (py * 4 + px))) & 3
                    if x < width and y < height:
                        dst = (y * width + x) * 4
                        out[dst:dst + 4] = bytes(colors[index])
    return bytes(out)


def decode_vtf(path: Path) -> tuple[int, int, bytes, int]:
    data = path.read_bytes()
    if len(data) < 64 or data[:4] != b"VTF\0":
        raise ValueError("not a valid VTF file (missing VTF signature)")
    major, minor, header_size = struct.unpack_from("<III", data, 4)
    if major != 7 or minor > 2:
        raise ValueError(f"VTF {major}.{minor} is not supported; expected 7.0-7.2")
    if header_size < 64 or header_size > len(data):
        raise ValueError("invalid VTF header size")
    width, height = struct.unpack_from("<HH", data, 16)
    flags = struct.unpack_from("<I", data, 20)[0]
    frames = struct.unpack_from("<H", data, 24)[0]
    high_fmt = struct.unpack_from("<i", data, 52)[0]
    mip_count = data[56]
    low_fmt = struct.unpack_from("<i", data, 57)[0]
    low_w, low_h = data[61], data[62]
    depth = struct.unpack_from("<H", data, 63)[0] if minor >= 2 and header_size >= 65 else 1

    if not width or not height or width > 1024 or height > 1024:
        raise ValueError(f"texture dimensions {width}x{height} are outside 1..1024")
    if frames != 1:
        raise ValueError(f"animated VTF ({frames} frames) is not supported yet")
    if depth != 1:
        raise ValueError(f"3D VTF texture depth {depth} is not supported")
    if flags & VTF_ENVMAP:
        raise ValueError("cubemap VTF textures are not supported")
    if not 1 <= mip_count <= 16:
        raise ValueError(f"invalid mipmap count {mip_count}")

    low_size = image_size(low_fmt, low_w, low_h) if low_fmt >= 0 and low_w and low_h else 0
    offset = header_size + low_size
    # VTF stores mip levels from smallest to largest; skip all smaller levels.
    for level in range(mip_count - 1, 0, -1):
        offset += image_size(high_fmt, max(1, width >> level), max(1, height >> level))
    top_size = image_size(high_fmt, width, height)
    if offset + top_size > len(data):
        raise ValueError("VTF image payload is truncated or has an unsupported layout")
    raw = data[offset:offset + top_size]

    if high_fmt == FMT_DXT1:
        rgba = decode_dxt1(raw, width, height)
    else:
        rgba = bytearray(width * height * 4)
        src_bpp = 3 if high_fmt in (FMT_RGB888, FMT_BGR888) else 4
        for i in range(width * height):
            p = i * src_bpp
            if high_fmt == FMT_RGBA8888:
                r, g, b, a = raw[p:p + 4]
            elif high_fmt == FMT_BGRA8888:
                b, g, r, a = raw[p:p + 4]
            elif high_fmt == FMT_ABGR8888:
                a, b, g, r = raw[p:p + 4]
            elif high_fmt == FMT_RGB888:
                r, g, b = raw[p:p + 3]
                a = 255
            elif high_fmt == FMT_BGR888:
                b, g, r = raw[p:p + 3]
                a = 255
            else:
                raise ValueError(f"unsupported VTF image format {high_fmt}")
            rgba[i * 4:i * 4 + 4] = bytes((r, g, b, a))
        rgba = bytes(rgba)
    return width, height, rgba, high_fmt


def rgba_to_5551(rgba: bytes) -> bytes:
    out = bytearray(len(rgba) // 2)
    for i in range(0, len(rgba), 4):
        r, g, b, a = rgba[i:i + 4]
        value = ((r >> 3) | ((g >> 3) << 5) |
                 ((b >> 3) << 10) | ((1 if a >= 128 else 0) << 15))
        struct.pack_into("<H", out, (i // 4) * 2, value)
    return bytes(out)


def convert(source: Path, destination: Path) -> tuple[int, int, int]:
    width, height, rgba, source_format = decode_vtf(source)
    pixels = rgba_to_5551(rgba)
    header = struct.pack("<4sHHHHII", b"H2TX", 1, width, height, 1,
                         source_format, len(pixels))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(header + pixels)
    return width, height, source_format


def self_test() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp) / "sample.vtf"
        target = Path(temp) / "sample.h2tx"
        header = bytearray(64)
        header[:4] = b"VTF\0"
        struct.pack_into("<III", header, 4, 7, 0, 64)
        struct.pack_into("<HHIHH", header, 16, 2, 2, 0, 1, 0)
        struct.pack_into("<i", header, 52, FMT_RGBA8888)
        header[56] = 1
        struct.pack_into("<i", header, 57, -1)
        source.write_bytes(header + bytes([
            255, 0, 0, 255, 0, 255, 0, 255,
            0, 0, 255, 255, 255, 255, 255, 0,
        ]))
        convert(source, target)
        result = target.read_bytes()
        assert result[:4] == b"H2TX"
        assert len(result) == 20 + 8
        assert struct.unpack_from("<HH", result, 6) == (2, 2)

        # A solid-red 4x4 DXT1 block exercises the compressed decoder.
        dxt = bytearray(64)
        dxt[:4] = b"VTF\0"
        struct.pack_into("<III", dxt, 4, 7, 0, 64)
        struct.pack_into("<HHIHH", dxt, 16, 4, 4, 0, 1, 0)
        struct.pack_into("<i", dxt, 52, FMT_DXT1)
        dxt[56] = 1
        struct.pack_into("<i", dxt, 57, -1)
        dxt.extend(struct.pack("<HHI", 0xF800, 0x0000, 0))
        source.write_bytes(dxt)
        convert(source, target)
        assert len(target.read_bytes()) == 20 + 4 * 4 * 2
    print("VTF converter self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        if args.input is None or args.output is None:
            parser.error("input and output are required unless --self-test is used")
        width, height, fmt = convert(args.input, args.output)
        print(f"Converted {args.input}: {width}x{height}, VTF format {fmt}")
        print(f"Output: {args.output} (H2TX / RGBA5551 / linear PSMCT16)")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
