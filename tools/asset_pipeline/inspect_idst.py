#!/usr/bin/env python3
"""Read-only validator for the common Source IDST MDL file header.

This does not decode mesh data. A usable Source model normally also needs its
matching VVD and VTX companions, which must be identified before conversion.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 80 or data[:4] != b"IDST":
        raise ValueError("not a Source MDL file (expected IDST header)")
    version, checksum = struct.unpack_from("<ii", data, 4)
    raw_name = data[12:76].split(b"\0", 1)[0]
    name = raw_name.decode("utf-8", errors="replace")
    declared_length = struct.unpack_from("<i", data, 76)[0]
    if version <= 0 or version > 100:
        raise ValueError(f"implausible Source MDL version {version}")
    if declared_length < 80 or declared_length > len(data):
        raise ValueError(
            f"invalid declared MDL length {declared_length} for {len(data)}-byte file"
        )
    return {
        "file": str(path),
        "signature": "IDST",
        "version": version,
        "checksum": f"0x{checksum & 0xffffffff:08X}",
        "model_name": name,
        "declared_length": declared_length,
        "actual_length": len(data),
        "has_trailing_data": len(data) > declared_length,
        "conversion_status": "header_validated_mesh_not_decoded",
        "required_companions": [path.with_suffix(".vvd").name, path.with_suffix(".dx90.vtx").name],
    }


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        sample = Path(temp) / "sample.mdl"
        header = bytearray(80)
        header[:4] = b"IDST"
        struct.pack_into("<ii", header, 4, 48, 0x12345678)
        header[12:22] = b"sample.mdl"
        struct.pack_into("<i", header, 76, 80)
        sample.write_bytes(header)
        result = inspect(sample)
        assert result["version"] == 48
        assert result["model_name"] == "sample.mdl"
        assert result["conversion_status"] == "header_validated_mesh_not_decoded"
    print("IDST inspector self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            return 0
        if args.input is None:
            parser.error("input is required unless --self-test is used")
        result = inspect(args.input)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for key, value in result.items():
                print(f"{key}: {value}")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
