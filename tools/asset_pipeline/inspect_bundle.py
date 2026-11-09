#!/usr/bin/env python3
"""Safely inspect PSP/Source-style asset bundles without extracting them."""
from __future__ import annotations
import argparse
import json
import struct
import zipfile
from pathlib import Path

KNOWN = {
    b"PADN": "SandstoneMod PADN container",
    b"PSR2": "SandstoneMod PSR2 map bundle",
    b"PSTO": "SandstoneMod PSTO store",
    b"PVMD": "SandstoneMod viewmodel bundle",
    b"IDST": "Source MDL model",
    b"VTF\x00": "Valve Texture Format",
    b"PSND": "PSND audio sub-container (observed inside PADN)",
    b"PSRC": "PSRC resource sub-container (observed inside PADN)",
    b"SCRP": "SandstoneMod script container (observed inside PADN)",
    b"\x7fELF": "ELF executable/module",
    b"\x00PBP": "PSP EBOOT.PBP executable container",
}


def describe(name: str, size: int, head: bytes) -> dict:
    sig = head[:4]
    inner = None
    if sig == b"PADN" and len(head) >= 0x44:
        inner_sig = head[0x40:0x44]
        inner = KNOWN.get(inner_sig, inner_sig.decode("ascii", "replace"))
    version = struct.unpack_from("<I", head, 4)[0] if len(head) >= 8 else None
    return {
        "path": name,
        "size": size,
        "signature_hex": sig.hex(),
        "signature_ascii": sig.decode("ascii", "replace"),
        "format": KNOWN.get(sig, "unknown"),
        "version_or_header_word": version,
        "embedded_format_at_0x40": inner,
    }


def inspect_zip(path: Path) -> dict:
    rows = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            with archive.open(info) as stream:
                head = stream.read(0x80)
            rows.append(describe(info.filename, info.file_size, head))
    return {
        "archive": str(path),
        "files": len(rows),
        "uncompressed_bytes": sum(item["size"] for item in rows),
        "entries": rows,
    }


def inspect_file(path: Path) -> dict:
    with path.open("rb") as stream:
        head = stream.read(0x80)
    return {
        "archive": str(path),
        "files": 1,
        "uncompressed_bytes": path.stat().st_size,
        "entries": [describe(path.name, path.stat().st_size, head)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="ZIP bundle or individual asset")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"input does not exist or is not a file: {args.input}")
    result = inspect_zip(args.input) if zipfile.is_zipfile(args.input) else inspect_file(args.input)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Archive: {result['archive']}\nFiles: {result['files']}\n"
              f"Uncompressed: {result['uncompressed_bytes']:,} bytes")
        for item in result["entries"]:
            print(f"{item['size']:>12,}  {item['signature_ascii']!r:<8}  "
                  f"{item['format']}: {item['path']}")
            if item["embedded_format_at_0x40"]:
                print(f"             embedded @0x40: {item['embedded_format_at_0x40']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
