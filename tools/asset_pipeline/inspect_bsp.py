#!/usr/bin/env python3
"""Inspect Source 1 and GoldSrc BSP headers without extracting or modifying the map."""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Callable

SOURCE_MAGIC = b"VBSP"
SOURCE_MIN_VERSION = 19
SOURCE_MAX_VERSION = 21
SOURCE_LUMP_COUNT = 64
SOURCE_HEADER_SIZE = 8 + SOURCE_LUMP_COUNT * 16 + 4

GOLDSRC_VERSION = 30
GOLDSRC_LUMP_COUNT = 15
GOLDSRC_HEADER_SIZE = 4 + GOLDSRC_LUMP_COUNT * 8


def _check_lump(index: int, offset: int, length: int, header_size: int, file_size: int) -> None:
    if offset < 0 or length < 0:
        raise ValueError(f"lump {index}: negative offset or length")
    if length == 0:
        return
    if offset < header_size:
        raise ValueError(f"lump {index}: data overlaps the {header_size}-byte header")
    if offset + length > file_size:
        raise ValueError(
            f"lump {index}: range 0x{offset:X}..0x{offset + length:X} exceeds "
            f"file size 0x{file_size:X}"
        )


def inspect_header(
    header: bytes,
    file_size: int,
    read_at: Callable[[int, int], bytes] | None = None,
) -> dict:
    """Validate the format header and every lump range; read_at is used only for LZMA markers."""
    if file_size < 4 or len(header) < 4:
        raise ValueError("file is too small to contain a BSP header")

    if header[:4] == SOURCE_MAGIC:
        if len(header) < SOURCE_HEADER_SIZE or file_size < SOURCE_HEADER_SIZE:
            raise ValueError(f"truncated Source BSP header (need {SOURCE_HEADER_SIZE} bytes)")
        version = struct.unpack_from("<i", header, 4)[0]
        if not SOURCE_MIN_VERSION <= version <= SOURCE_MAX_VERSION:
            raise ValueError(
                f"Source VBSP version {version} is outside the audited converter range "
                f"{SOURCE_MIN_VERSION}-{SOURCE_MAX_VERSION}"
            )

        lumps = []
        compressed = 0
        for index in range(SOURCE_LUMP_COUNT):
            offset, length, lump_version, uncompressed_size = struct.unpack_from(
                "<iiiI", header, 8 + index * 16
            )
            _check_lump(index, offset, length, SOURCE_HEADER_SIZE, file_size)
            is_lzma = False
            if length >= 4 and read_at is not None:
                is_lzma = read_at(offset, 4) == b"LZMA"
            if is_lzma:
                compressed += 1
            lumps.append({
                "index": index,
                "offset": offset,
                "size": length,
                "version": lump_version,
                "uncompressed_size": uncompressed_size,
                "lzma_marker": is_lzma,
            })

        revision = struct.unpack_from("<i", header, 8 + SOURCE_LUMP_COUNT * 16)[0]
        return {
            "format": "Source 1 VBSP",
            "version": version,
            "revision": revision,
            "header_size": SOURCE_HEADER_SIZE,
            "file_size": file_size,
            "lump_count": SOURCE_LUMP_COUNT,
            "non_empty_lumps": sum(1 for lump in lumps if lump["size"]),
            "lzma_lumps": compressed,
            "lumps": lumps,
            "note": "The header cannot identify the specific Source game (for example Half-Life: Source).",
        }

    version = struct.unpack_from("<i", header, 0)[0]
    if version == GOLDSRC_VERSION:
        if len(header) < GOLDSRC_HEADER_SIZE or file_size < GOLDSRC_HEADER_SIZE:
            raise ValueError(f"truncated GoldSrc BSP header (need {GOLDSRC_HEADER_SIZE} bytes)")
        lumps = []
        for index in range(GOLDSRC_LUMP_COUNT):
            offset, length = struct.unpack_from("<ii", header, 4 + index * 8)
            _check_lump(index, offset, length, GOLDSRC_HEADER_SIZE, file_size)
            lumps.append({"index": index, "offset": offset, "size": length})
        return {
            "format": "GoldSrc BSP",
            "version": version,
            "revision": 0,
            "header_size": GOLDSRC_HEADER_SIZE,
            "file_size": file_size,
            "lump_count": GOLDSRC_LUMP_COUNT,
            "non_empty_lumps": sum(1 for lump in lumps if lump["size"]),
            "lzma_lumps": 0,
            "lumps": lumps,
            "note": "GoldSrc is a separate format; it is not a Source VBSP map.",
        }

    signature = header[:4].decode("ascii", "replace")
    raise ValueError(f"unsupported BSP signature/version: {signature!r} / {version}")


def inspect_file(path: Path) -> dict:
    file_size = path.stat().st_size
    with path.open("rb") as stream:
        prefix = stream.read(SOURCE_HEADER_SIZE)
        header = prefix if prefix[:4] == SOURCE_MAGIC else prefix[:GOLDSRC_HEADER_SIZE]

        def read_at(offset: int, size: int) -> bytes:
            stream.seek(offset)
            return stream.read(size)

        return inspect_header(header, file_size, read_at)


def _make_source(version: int = 19) -> bytes:
    header = bytearray(SOURCE_HEADER_SIZE)
    struct.pack_into("<4si", header, 0, SOURCE_MAGIC, version)
    struct.pack_into("<i", header, 8 + SOURCE_LUMP_COUNT * 16, 0)
    return bytes(header)


def _make_goldsrc() -> bytes:
    header = bytearray(GOLDSRC_HEADER_SIZE)
    struct.pack_into("<i", header, 0, GOLDSRC_VERSION)
    return bytes(header)


def self_test() -> None:
    source = inspect_header(_make_source(), SOURCE_HEADER_SIZE)
    assert source["format"] == "Source 1 VBSP"
    assert source["version"] == 19
    assert source["lump_count"] == 64

    source21 = inspect_header(_make_source(21), SOURCE_HEADER_SIZE)
    assert source21["version"] == 21

    goldsrc = inspect_header(_make_goldsrc(), GOLDSRC_HEADER_SIZE)
    assert goldsrc["format"] == "GoldSrc BSP"
    assert goldsrc["lump_count"] == 15

    bad_range = bytearray(_make_source())
    struct.pack_into("<iiiI", bad_range, 8, SOURCE_HEADER_SIZE, 8, 0, 0)
    try:
        inspect_header(bytes(bad_range), SOURCE_HEADER_SIZE)
    except ValueError as exc:
        assert "exceeds file size" in str(exc)
    else:
        raise AssertionError("out-of-bounds Source lump was accepted")

    try:
        inspect_header(_make_source(17), SOURCE_HEADER_SIZE)
    except ValueError as exc:
        assert "outside the audited converter range" in str(exc)
    else:
        raise AssertionError("unsupported Source BSP version was accepted")

    try:
        inspect_header(b"VBSP", 4)
    except ValueError as exc:
        assert "truncated Source BSP header" in str(exc)
    else:
        raise AssertionError("truncated Source BSP header was accepted")

    print("BSP header inspector self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            self_test()
            return 0
        if args.input is None:
            parser.error("input is required unless --self-test is used")
        result = inspect_file(args.input)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"{result['format']} v{result['version']}")
            print(f"File: {result['file_size']:,} bytes; header: {result['header_size']} bytes")
            print(f"Lumps: {result['non_empty_lumps']}/{result['lump_count']} non-empty")
            if result["format"] == "Source 1 VBSP":
                print(f"LZMA-marked lumps: {result['lzma_lumps']}")
            print(result["note"])
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
