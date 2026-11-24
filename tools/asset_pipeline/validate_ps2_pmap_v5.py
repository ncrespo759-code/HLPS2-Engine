#!/usr/bin/env python3
"""Validate PMAP v5 files against the legacy PS2-GMOD runtime's section layouts.

This checks a converted map container before packaging it for PS2. It does not
extract game assets and does not load or execute the map in the game runtime.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

MAGIC = b"PMAP"
VERSION = 5
ALIGNMENT = 16
MAX_FILE_SIZE = 0x7FFFFFFF
SIDE_INDEX_MASK = 0x7FFFFFFF

ITEM_SIZES = {
    b"INFO": 96, b"SPWN": 16, b"TEXS": 32, b"VERT": 16, b"INDX": 2,
    b"BTCH": 80, b"PLAN": 16, b"NODE": 12, b"LEAF": 24,
    b"BRSH": 12, b"BSID": 4, b"LBRS": 4, b"ENTS": 128,
    b"EBAT": 80, b"EBRL": 4, b"EOUT": 16, b"SPRP": 64,
    b"PHYS": 32, b"LSTY": 16, b"LSTP": 64, b"SKYT": 4,
}
REQUIRED = tuple(ITEM_SIZES) + (b"TXDT", b"PVS ", b"SPVS")


class FormatError(ValueError):
    pass


def align(n: int) -> int:
    return (n + ALIGNMENT - 1) & ~(ALIGNMENT - 1)


def parse_container(data: bytes) -> dict[bytes, dict]:
    if len(data) < 16:
        raise FormatError("truncated PMAP header")
    if len(data) > MAX_FILE_SIZE:
        raise FormatError("file exceeds the PS2 signed 32-bit offset limit")
    magic, version, count, _reserved = struct.unpack_from("<4sIII", data, 0)
    if magic != MAGIC:
        raise FormatError("not a PMAP file")
    if version != VERSION:
        raise FormatError(f"expected PMAP v{VERSION}, found v{version}")
    if count > 64:
        raise FormatError(f"unreasonable section count: {count}")
    table_end = 16 + count * 16
    if table_end > len(data):
        raise FormatError("section table extends beyond end of file")
    min_offset = align(table_end)
    sections = {}
    ranges = []
    for i in range(count):
        sid, offset, size, item_count = struct.unpack_from("<4sIII", data, 16 + i * 16)
        if sid in sections:
            raise FormatError(f"duplicate section {sid!r}")
        end = offset + size
        if offset < min_offset or offset % ALIGNMENT:
            raise FormatError(f"section {sid!r} has an invalid or unaligned offset")
        if end > len(data):
            raise FormatError(f"section {sid!r} extends beyond end of file")
        if size:
            ranges.append((offset, end, sid))
        sections[sid] = {"offset": offset, "size": size, "count": item_count,
                         "data": data[offset:end]}
    ranges.sort()
    for prev, cur in zip(ranges, ranges[1:]):
        if cur[0] < prev[1]:
            raise FormatError(f"sections {prev[2]!r} and {cur[2]!r} overlap")
    missing = [sid.decode("ascii", "replace") for sid in REQUIRED if sid not in sections]
    if missing:
        raise FormatError("missing runtime sections: " + ", ".join(missing))
    if b"PVSZ" in sections or b"SPVZ" in sections:
        raise FormatError("v6 compressed visibility sections are not valid in a v5 file")
    return sections


def section_count(sections: dict, sid: bytes, item_size: int | None = None) -> int:
    sec = sections[sid]
    if item_size is not None and sec["size"] != sec["count"] * item_size:
        raise FormatError(
            f"{sid.decode('ascii', 'replace')} size {sec['size']} does not match "
            f"{sec['count']} records of {item_size} bytes"
        )
    return sec["count"]


def check_range(first: int, count: int, limit: int, label: str) -> None:
    if first > limit or count > limit - first:
        raise FormatError(f"{label} range {first}+{count} exceeds {limit}")


def validate_texture_offsets(sections: dict, tex_count: int) -> None:
    txdt = sections[b"TXDT"]
    lo, hi = txdt["offset"], txdt["offset"] + txdt["size"]
    tex = sections[b"TEXS"]["data"]
    for i in range(tex_count):
        width, height, levels, _flags, _reserved, clut, *mips = struct.unpack_from("<HHBBHI5I", tex, i * 32)
        if not width or not height or not 1 <= levels <= 5:
            raise FormatError(f"texture {i} has invalid dimensions or mip count")
        if clut < lo or clut + 1024 > hi:
            raise FormatError(f"texture {i} CLUT is outside TXDT")
        for level in range(levels):
            w, h = max(1, width >> level), max(1, height >> level)
            ofs = mips[level]
            if ofs < lo or ofs + w * h > hi:
                raise FormatError(f"texture {i} mip {level} is outside TXDT")


def validate_batches(sections: dict, sid: bytes, batch_count: int,
                     vertex_count: int, index_count: int, texture_count: int) -> None:
    raw = sections[sid]["data"]
    indices = sections[b"INDX"]["data"]
    for i in range(batch_count):
        first_vertex, first_index, num_indices, tex, _flags = struct.unpack_from("<IIIHH", raw, i * 80)
        check_range(first_index, num_indices, index_count, f"{sid.decode()} batch {i} index")
        if num_indices % 3:
            raise FormatError(f"{sid.decode()} batch {i} index count is not a triangle list")
        if num_indices and tex >= texture_count:
            raise FormatError(f"{sid.decode()} batch {i} references missing texture {tex}")
        for j in range(first_index, first_index + num_indices):
            relative = struct.unpack_from("<H", indices, j * 2)[0]
            if first_vertex + relative >= vertex_count:
                raise FormatError(f"{sid.decode()} batch {i} references vertex {first_vertex + relative} out of range")


def validate_bytes(data: bytes) -> dict:
    s = parse_container(data)
    counts = {}
    for sid, item_size in ITEM_SIZES.items():
        counts[sid.decode("ascii")] = section_count(s, sid, item_size)

    info = s[b"INFO"]["data"]
    if s[b"INFO"]["count"] != 1:
        raise FormatError("INFO must contain exactly one record")
    tier, pvs_words = struct.unpack_from("<II", info, 0)
    sprp_words = struct.unpack_from("<I", info, 76)[0]
    if tier != 0:
        raise FormatError("PS2 32 MB validation requires the low-detail tier (INFO.tier = 0)")

    clusters = section_count(s, b"PVS ")
    if s[b"PVS "]["size"] != clusters * pvs_words * 4:
        raise FormatError("PVS byte size does not match cluster count and INFO.pvs_row_words")
    if pvs_words * 32 < counts["BTCH"]:
        raise FormatError("PVS row width cannot address every world batch")
    if counts["BTCH"] and pvs_words == 0:
        raise FormatError("world batches exist but PVS row width is zero")

    if sprp_words:
        if s[b"SPVS"]["count"] != clusters or s[b"SPVS"]["size"] != clusters * sprp_words * 4:
            raise FormatError("SPVS byte size/count does not match clusters and INFO.sprp_row_words")
    elif s[b"SPVS"]["count"] != 0 or s[b"SPVS"]["size"] != 0:
        raise FormatError("SPVS must be empty when INFO.sprp_row_words is zero")
    if sprp_words * 32 < counts["SPRP"]:
        raise FormatError("SPVS row width cannot address every static prop")

    validate_texture_offsets(s, counts["TEXS"])
    validate_batches(s, b"BTCH", counts["BTCH"], counts["VERT"], counts["INDX"], counts["TEXS"])
    validate_batches(s, b"EBAT", counts["EBAT"], counts["VERT"], counts["INDX"], counts["TEXS"])

    planes, nodes, leaves = counts["PLAN"], counts["NODE"], counts["LEAF"]
    if leaves == 0:
        raise FormatError("LEAF must contain at least one record; the runtime starts at leaf zero")
    for i in range(nodes):
        plane, child0, child1 = struct.unpack_from("<iii", s[b"NODE"]["data"], i * 12)
        if not 0 <= plane < planes:
            raise FormatError(f"NODE {i} references missing plane {plane}")
        for child in (child0, child1):
            if child >= 0 and child >= nodes:
                raise FormatError(f"NODE {i} references missing child node {child}")
            if child < 0 and -1 - child >= leaves:
                raise FormatError(f"NODE {i} references missing leaf {-1 - child}")

    brushes, sides, leaf_brushes = counts["BRSH"], counts["BSID"], counts["LBRS"]
    for i in range(leaves):
        cluster, _contents, first, num, _ambient, _reserved = struct.unpack_from(
            "<iIIIII", s[b"LEAF"]["data"], i * 24)
        if cluster != -1 and not 0 <= cluster < clusters:
            raise FormatError(f"LEAF {i} references missing PVS cluster {cluster}")
        check_range(first, num, leaf_brushes, f"LEAF {i} brush")
    for i in range(leaf_brushes):
        bi = struct.unpack_from("<I", s[b"LBRS"]["data"], i * 4)[0]
        if bi >= brushes:
            raise FormatError(f"LBRS entry {i} references missing brush {bi}")

    for i in range(brushes):
        first, num, _contents = struct.unpack_from("<III", s[b"BRSH"]["data"], i * 12)
        if num > 64:
            raise FormatError(f"BRSH {i} exceeds the PS2 runtime's 64-plane brush limit")
        check_range(first, num, sides, f"BRSH {i} side")
    for i in range(sides):
        side = struct.unpack_from("<I", s[b"BSID"]["data"], i * 4)[0]
        plane = side & SIDE_INDEX_MASK
        if plane >= planes:
            raise FormatError(f"BSID entry {i} references missing plane {plane}")

    ents = counts["ENTS"]
    for i in range(ents):
        rec = s[b"ENTS"]["data"][i * 128:(i + 1) * 128]
        kind, flags = struct.unpack_from("<II", rec, 0)
        if not 1 <= kind <= 6:
            raise FormatError(f"ENTS {i} has unsupported v5 entity type {kind}")
        if flags & 0x40000000:
            raise FormatError(f"ENTS {i} contains the v6 locked-door flag")
        first_batch, num_batches, first_brush, num_brushes, first_output, num_outputs = struct.unpack_from(
            "<6I", rec, 104)
        check_range(first_batch, num_batches, counts["EBAT"], f"ENTS {i} batch")
        check_range(first_brush, num_brushes, counts["EBRL"], f"ENTS {i} brush")
        check_range(first_output, num_outputs, counts["EOUT"], f"ENTS {i} output")

    for i in range(counts["EBRL"]):
        bi = struct.unpack_from("<I", s[b"EBRL"]["data"], i * 4)[0]
        if bi >= brushes:
            raise FormatError(f"EBRL entry {i} references missing brush {bi}")
    for i in range(counts["EOUT"]):
        event, target, input_id = struct.unpack_from("<IiI", s[b"EOUT"]["data"], i * 16)
        if event > 2 or not 1 <= input_id <= 7:
            raise FormatError(f"EOUT {i} uses an event/input unavailable in the PS2 v5 runtime")
        if target != -1 and not 0 <= target < ents:
            raise FormatError(f"EOUT {i} references missing entity {target}")

    for i in range(counts["SPRP"]):
        parent = struct.unpack_from("<I", s[b"SPRP"]["data"], i * 64 + 60)[0]
        if parent:
            raise FormatError(f"SPRP {i} uses a v6 parent field not present in PS2 v5")
    for i in range(counts["LSTY"]):
        vertex, _base, style = struct.unpack_from("<IIH", s[b"LSTY"]["data"], i * 16)
        if vertex >= counts["VERT"] or style >= 64:
            raise FormatError(f"LSTY {i} references an invalid vertex or light style")
    if counts["LSTP"] != 64 or s[b"LSTP"]["size"] != 4096:
        raise FormatError("LSTP must contain 64 fixed 64-byte light-style patterns")
    sky = struct.unpack_from("<i", s[b"SKYT"]["data"], 0)[0]
    if sky != -1 and not (0 <= sky and sky + 6 <= counts["TEXS"]):
        raise FormatError("SKYT references an incomplete six-texture skybox")

    return {
        "format": "PMAP v5 (PS2-GMOD runtime layout)",
        "file_size": len(data),
        "tier": tier,
        "clusters": clusters,
        "world_batches": counts["BTCH"],
        "vertices": counts["VERT"],
        "indices": counts["INDX"],
        "textures": counts["TEXS"],
        "brushes": brushes,
        "static_props": counts["SPRP"],
        "entities": ents,
    }


def _pack_sections(sections):
    offset = align(16 + len(sections) * 16)
    table = []
    for sid, data, count in sections:
        table.append((sid, offset, len(data), count))
        offset = align(offset + len(data))
    out = bytearray(offset)
    struct.pack_into("<4sIII", out, 0, MAGIC, VERSION, len(sections), 0)
    for i, (sid, ofs, size, count) in enumerate(table):
        struct.pack_into("<4sIII", out, 16 + i * 16, sid, ofs, size, count)
    for (_sid, payload, _count), (_sid2, ofs, size, _count2) in zip(sections, table):
        out[ofs:ofs + size] = payload
    return bytes(out), {sid: ofs for sid, ofs, _size, _count in table}


def _read_table(data):
    count = struct.unpack_from("<I", data, 8)[0]
    return [struct.unpack_from("<4sIII", data, 16 + i * 16) for i in range(count)]


def self_test():
    info = bytearray(96)
    struct.pack_into("<II", info, 0, 0, 1)  # low tier, one PVS word per cluster
    sections = [
        (b"INFO", bytes(info), 1),
        (b"SPWN", bytes(16), 1),
        (b"TEXS", bytes(32), 1),
        (b"TXDT", bytes(1088), 1088),
        (b"VERT", bytes(48), 3),
        (b"INDX", struct.pack("<3H", 0, 1, 2), 3),
        (b"BTCH", bytes(80), 1),
        (b"PLAN", bytes(16), 1),
        (b"NODE", b"", 0),
        (b"LEAF", struct.pack("<iIIIII", 0, 0, 0, 0, 0, 0), 1),
        (b"PVS ", struct.pack("<I", 1), 1),
        (b"BRSH", b"", 0),
        (b"BSID", b"", 0),
        (b"LBRS", b"", 0),
        (b"ENTS", b"", 0),
        (b"EBAT", b"", 0),
        (b"EBRL", b"", 0),
        (b"EOUT", b"", 0),
        (b"SPRP", b"", 0),
        (b"SPVS", b"", 0),
        (b"PHYS", b"", 0),
        (b"LSTY", b"", 0),
        (b"LSTP", bytes(4096), 64),
        (b"SKYT", struct.pack("<i", -1), 1),
    ]
    # Make one valid 8x8 paletted texture: 1 KB CLUT and 64 bytes of pixels in TXDT.
    _raw, offsets = _pack_sections(sections)
    tex = struct.pack("<HHBBHI5I", 8, 8, 1, 0, 0, offsets[b"TXDT"], offsets[b"TXDT"] + 1024, 0, 0, 0, 0)
    sections[2] = (b"TEXS", tex, 1)
    # One world batch referencing the triangle and texture zero.
    batch = bytearray(80)
    struct.pack_into("<IIIHH", batch, 0, 0, 0, 3, 0, 0)
    sections[6] = (b"BTCH", bytes(batch), 1)
    raw, _ = _pack_sections(sections)
    result = validate_bytes(raw)
    assert result["clusters"] == 1 and result["world_batches"] == 1

    bad_version = bytearray(raw)
    struct.pack_into("<I", bad_version, 4, 6)
    try:
        validate_bytes(bytes(bad_version))
    except FormatError as exc:
        assert "expected PMAP v5" in str(exc)
    else:
        raise AssertionError("v6 PMAP was accepted as v5")

    bad_index = bytearray(raw)
    index_offset = next(ofs for sid, ofs, _size, _count in _read_table(raw) if sid == b"INDX")
    struct.pack_into("<H", bad_index, index_offset, 3)
    try:
        validate_bytes(bytes(bad_index))
    except FormatError as exc:
        assert "out of range" in str(exc)
    else:
        raise AssertionError("out-of-range batch vertex was accepted")

    bad_overlap = bytearray(raw)
    info_offset = next(ofs for sid, ofs, _size, _count in _read_table(raw) if sid == b"INFO")
    spwn_entry = 16 + 1 * 16
    struct.pack_into("<I", bad_overlap, spwn_entry + 4, info_offset)
    try:
        validate_bytes(bytes(bad_overlap))
    except FormatError as exc:
        assert "overlap" in str(exc)
    else:
        raise AssertionError("overlapping PMAP sections were accepted")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, help="PMAP v5 file to validate")
    parser.add_argument("--self-test", action="store_true", help="run synthetic validator tests")
    parser.add_argument("--json", action="store_true", help="print machine-readable summary")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            self_test()
            print("PMAP v5 validator self-test: OK")
            return 0
        if args.path is None:
            parser.error("path is required unless --self-test is used")
        result = validate_bytes(args.path.read_bytes())
        print(json.dumps(result, indent=2) if args.json else
              f"OK: PMAP v5, {result['clusters']} clusters, {result['world_batches']} batches, "
              f"{result['vertices']} vertices, {result['textures']} textures, {result['file_size']} bytes")
        return 0
    except (OSError, FormatError, struct.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
