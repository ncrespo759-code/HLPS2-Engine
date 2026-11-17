#!/usr/bin/env python3
"""Convert Retcon's PMAP v6 maps to the legacy PS2-GMOD PMAP v5 layout.

This is a host-side compatibility exporter, not a game-asset extractor. It does
not read BSP/MDL/VTF files and does not include any copyrighted game content.
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
from pathlib import Path

MAGIC = b"PMAP"
INPUT_VERSION = 6
OUTPUT_VERSION = 5
BOX_BEVELS = 0x80000000
SIDE_BEVEL = 0x80000000
SIDE_INDEX_MASK = 0x7FFFFFFF
ALIGNMENT = 16
MAX_FILE_SIZE = 0x7FFFFFFF

REQUIRED = (
    b"INFO", b"SPWN", b"TEXS", b"TXDT", b"VERT", b"INDX", b"BTCH",
    b"PLAN", b"NODE", b"LEAF", b"PVSZ", b"BRSH", b"BSID", b"LBRS",
    b"ENTS", b"EBAT", b"EBRL", b"EOUT", b"SPRP", b"SPVZ", b"PHYS",
    b"LSTY", b"LSTP", b"SKYT",
)

class FormatError(ValueError):
    pass


def align(value: int) -> int:
    return (value + ALIGNMENT - 1) & ~(ALIGNMENT - 1)


def parse_container(data: bytes, expected_version=INPUT_VERSION, required=REQUIRED):
    if len(data) < 16:
        raise FormatError("truncated PMAP header")
    magic, version, count, _reserved = struct.unpack_from("<4sIII", data, 0)
    if magic != MAGIC:
        raise FormatError("input is not a PMAP file")
    if version != expected_version:
        raise FormatError(f"expected PMAP v{expected_version}, found v{version}")
    table_end = 16 + count * 16
    if table_end > len(data):
        raise FormatError("section table extends beyond end of file")
    min_offset = align(table_end)
    sections = []
    seen = set()
    ranges = []
    for index in range(count):
        sid, offset, size, item_count = struct.unpack_from("<4sIII", data, 16 + index * 16)
        if sid in seen:
            raise FormatError(f"duplicate section {sid!r}")
        seen.add(sid)
        if offset < min_offset or offset % ALIGNMENT:
            raise FormatError(f"section {sid!r} has an invalid or unaligned offset")
        end = offset + size
        if end > len(data):
            raise FormatError(f"section {sid!r} extends beyond end of file")
        if size:
            ranges.append((offset, end, sid))
        sections.append({"id": sid, "data": data[offset:end], "count": item_count, "old_offset": offset})
    ranges.sort()
    for previous, current in zip(ranges, ranges[1:]):
        if current[0] < previous[1]:
            raise FormatError(f"sections {previous[2]!r} and {current[2]!r} overlap")
    missing = [sid.decode("ascii", "replace") for sid in required if sid not in seen]
    if missing:
        raise FormatError("missing runtime sections: " + ", ".join(missing))
    return sections


def by_id(sections, sid):
    for section in sections:
        if section["id"] == sid:
            return section
    raise FormatError(f"missing section {sid!r}")


def require_size(section, expected: int, label: str):
    if len(section["data"]) != expected:
        raise FormatError(f"{label} has {len(section['data'])} bytes; expected {expected}")


def decode_rows(section: bytes, count: int, row_bytes: int, label: str) -> bytes:
    if count == 0:
        if section:
            raise FormatError(f"{label} has data but declares zero rows")
        return b""
    if row_bytes <= 0:
        raise FormatError(f"{label} declares rows but INFO has a zero row width")
    table_size = count * 4
    if table_size > len(section):
        raise FormatError(f"{label} row-offset table is truncated")
    output = bytearray()
    for row_index in range(count):
        offset = struct.unpack_from("<I", section, row_index * 4)[0]
        if offset < table_size or offset >= len(section):
            raise FormatError(f"{label} row {row_index} has an invalid data offset")
        cursor = offset
        row = bytearray()
        while len(row) < row_bytes:
            if cursor >= len(section):
                raise FormatError(f"{label} row {row_index} ends before {row_bytes} bytes")
            value = section[cursor]
            cursor += 1
            if value in (0, 255):
                if cursor >= len(section):
                    raise FormatError(f"{label} row {row_index} has a truncated run")
                run = section[cursor]
                cursor += 1
                if run == 0 or len(row) + run > row_bytes:
                    raise FormatError(f"{label} row {row_index} has an invalid run length")
                row.extend(bytes((value,)) * run)
            else:
                row.append(value)
        output.extend(row)
    return bytes(output)


def validate_v5_semantics(sections):
    ents = by_id(sections, b"ENTS")
    if len(ents["data"]) != ents["count"] * 128:
        raise FormatError("ENTS size does not match the v6 128-byte entity records")
    for index in range(ents["count"]):
        flags = struct.unpack_from("<I", ents["data"], index * 128 + 4)[0]
        if flags & 0x40000000:
            raise FormatError(
                f"entity {index} uses the v6 locked-door flag; the PS2 v5 runtime cannot preserve it"
            )

    outputs = by_id(sections, b"EOUT")
    if len(outputs["data"]) != outputs["count"] * 16:
        raise FormatError("EOUT size does not match its 16-byte records")
    for index in range(outputs["count"]):
        event, _target, input_id = struct.unpack_from("<IiI", outputs["data"], index * 16)
        if event > 2 or input_id < 1 or input_id > 7:
            raise FormatError(
                f"output {index} uses a v6 event/input not supported by the PS2 v5 runtime"
            )

    props = by_id(sections, b"SPRP")
    if len(props["data"]) != props["count"] * 64:
        raise FormatError("SPRP size does not match its 64-byte records")
    for index in range(props["count"]):
        parent = struct.unpack_from("<I", props["data"], index * 64 + 60)[0]
        if parent:
            raise FormatError(
                f"static prop {index} is parented to an entity; the PS2 v5 runtime has no parented-prop field"
            )


def expand_box_bevels(sections):
    expanded = 0
    brushes = by_id(sections, b"BRSH")
    sides = by_id(sections, b"BSID")
    planes = by_id(sections, b"PLAN")
    require_size(brushes, brushes["count"] * 12, "BRSH")
    if len(sides["data"]) % 4:
        raise FormatError("BSID size is not a multiple of four")
    if len(planes["data"]) % 16:
        raise FormatError("PLAN size is not a multiple of sixteen")

    old_words = struct.unpack(f"<{len(sides['data']) // 4}I", sides["data"]) if sides["data"] else ()
    new_words = []
    new_planes = bytearray(planes["data"])
    plane_count = len(new_planes) // 16
    new_brushes = bytearray()

    for index in range(brushes["count"]):
        first, encoded_count, contents = struct.unpack_from("<III", brushes["data"], index * 12)
        boxed = bool(encoded_count & BOX_BEVELS)
        real_count = encoded_count & SIDE_INDEX_MASK if boxed else encoded_count
        if boxed and real_count > 58:
            raise FormatError(f"brush {index} has more than 58 real sides before six box bevels")
        if not boxed and real_count > 64:
            raise FormatError(f"brush {index} has more than 64 sides; PS2 v5 clips at 64")

        extra = 6 if boxed else 0
        needed = real_count + extra
        if first + needed > len(old_words):
            raise FormatError(f"brush {index} side range exceeds BSID")
        source_sides = old_words[first:first + real_count]
        for side in source_sides:
            plane_index = side & SIDE_INDEX_MASK
            if plane_index >= plane_count:
                raise FormatError(f"brush {index} references missing plane {plane_index}")

        new_first = len(new_words)
        new_words.extend(source_sides)
        new_count = real_count

        if boxed:
            expanded += 1
            bounds_offset = (first + real_count) * 4
            bounds = struct.unpack_from("<6f", sides["data"], bounds_offset)
            mins, maxs = bounds[:3], bounds[3:]
            if not all(math.isfinite(v) for v in bounds):
                raise FormatError(f"brush {index} has non-finite box bevel bounds")
            if any(mins[axis] > maxs[axis] for axis in range(3)):
                raise FormatError(f"brush {index} has inverted box bevel bounds")
            bevel_planes = (
                (1.0, 0.0, 0.0, maxs[0]),
                (-1.0, 0.0, 0.0, -mins[0]),
                (0.0, 1.0, 0.0, maxs[1]),
                (0.0, -1.0, 0.0, -mins[1]),
                (0.0, 0.0, 1.0, maxs[2]),
                (0.0, 0.0, -1.0, -mins[2]),
            )
            for plane in bevel_planes:
                if plane_count >= SIDE_INDEX_MASK:
                    raise FormatError("PLAN has too many planes for the v5 side-index field")
                new_planes.extend(struct.pack("<4f", *plane))
                new_words.append(plane_count | SIDE_BEVEL)
                plane_count += 1
            new_count += 6

        if len(new_words) > 0xFFFFFFFF or new_first > 0xFFFFFFFF:
            raise FormatError("expanded BSID exceeds 32-bit section indices")
        new_brushes.extend(struct.pack("<III", new_first, new_count, contents))

    brushes["data"] = bytes(new_brushes)
    sides["data"] = struct.pack(f"<{len(new_words)}I", *new_words) if new_words else b""
    sides["count"] = len(new_words)
    planes["data"] = bytes(new_planes)
    planes["count"] = plane_count
    return expanded


def layout_sections(sections):
    offset = align(16 + 16 * len(sections))
    offsets = {}
    table = []
    for section in sections:
        sid, payload, count = section["id"], section["data"], section["count"]
        if len(payload) > 0xFFFFFFFF or count > 0xFFFFFFFF:
            raise FormatError(f"section {sid!r} exceeds 32-bit PMAP fields")
        offsets[sid] = offset
        table.append((sid, offset, len(payload), count))
        offset = align(offset + len(payload))
    if offset > MAX_FILE_SIZE:
        raise FormatError("converted PMAP exceeds the PS2 signed 32-bit file-offset limit")
    return offsets, table, offset


def adjust_texture_offsets(sections, old_txdt_offset, old_txdt_size, new_txdt_offset):
    textures = by_id(sections, b"TEXS")
    txdt = by_id(sections, b"TXDT")
    require_size(textures, textures["count"] * 32, "TEXS")
    if old_txdt_size != len(txdt["data"]):
        raise FormatError("TXDT size changed unexpectedly")
    data = bytearray(textures["data"])
    for index in range(textures["count"]):
        base = index * 32
        for field_offset in (8, 12, 16, 20, 24, 28):
            value = struct.unpack_from("<I", data, base + field_offset)[0]
            if value == 0:
                continue
            relative = value - old_txdt_offset
            if relative < 0 or relative >= old_txdt_size:
                raise FormatError(f"texture {index} contains an offset outside TXDT")
            adjusted = new_txdt_offset + relative
            if adjusted > 0xFFFFFFFF:
                raise FormatError("adjusted texture offset exceeds 32-bit range")
            struct.pack_into("<I", data, base + field_offset, adjusted)
    textures["data"] = bytes(data)


def write_container(sections):
    offsets, table, total_size = layout_sections(sections)
    output = bytearray(total_size)
    struct.pack_into("<4sIII", output, 0, MAGIC, OUTPUT_VERSION, len(sections), 0)
    for index, (sid, offset, size, count) in enumerate(table):
        struct.pack_into("<4sIII", output, 16 + index * 16, sid, offset, size, count)
    for section, (_, offset, size, _count) in zip(sections, table):
        output[offset:offset + size] = section["data"]
    return bytes(output), offsets


def convert_bytes(data: bytes):
    sections = parse_container(data)
    validate_v5_semantics(sections)

    info = by_id(sections, b"INFO")
    require_size(info, 96, "INFO")
    if info["count"] != 1:
        raise FormatError("INFO must contain exactly one record")
    pvs_words = struct.unpack_from("<I", info["data"], 4)[0]
    sprp_words = struct.unpack_from("<I", info["data"], 76)[0]

    pvsz = by_id(sections, b"PVSZ")
    spvsz = by_id(sections, b"SPVZ")
    pvs = decode_rows(pvsz["data"], pvsz["count"], pvs_words * 4, "PVSZ")
    if sprp_words:
        if spvsz["count"] != pvsz["count"]:
            raise FormatError("SPVZ row count does not match PVSZ cluster count")
        spvs = decode_rows(spvsz["data"], spvsz["count"], sprp_words * 4, "SPVZ")
    else:
        if spvsz["count"] != 0 or spvsz["data"]:
            raise FormatError("SPVZ must be empty when INFO sprp_row_words is zero")
        spvs = b""

    old_txdt = by_id(sections, b"TXDT")
    old_txdt_offset = old_txdt["old_offset"]
    old_txdt_size = len(old_txdt["data"])

    pvsz["id"], pvsz["data"], pvsz["count"] = b"PVS ", pvs, pvsz["count"]
    spvsz["id"], spvsz["data"], spvsz["count"] = b"SPVS", spvs, spvsz["count"]

    expanded = expand_box_bevels(sections)

    # Layout once to learn where TXDT moved after PLAN/BSID expansion, then fix
    # the absolute offsets stored in TEXS. TEXS itself keeps the same size.
    provisional_offsets, _table, _total = layout_sections(sections)
    adjust_texture_offsets(
        sections, old_txdt_offset, old_txdt_size, provisional_offsets[b"TXDT"]
    )
    output, offsets = write_container(sections)
    return output, {
        "input_bytes": len(data),
        "output_bytes": len(output),
        "clusters": pvsz["count"],
        "box_bevels_expanded": expanded,
        "txdt_offset": offsets[b"TXDT"],
    }


def _pack_sections(sections, version=INPUT_VERSION):
    offset = align(16 + 16 * len(sections))
    table = []
    for section in sections:
        table.append((section["id"], offset, len(section["data"]), section["count"]))
        offset = align(offset + len(section["data"]))
    output = bytearray(offset)
    struct.pack_into("<4sIII", output, 0, MAGIC, version, len(sections), 0)
    for index, (sid, section_offset, size, count) in enumerate(table):
        struct.pack_into("<4sIII", output, 16 + index * 16, sid, section_offset, size, count)
    for section, (_sid, section_offset, size, _count) in zip(sections, table):
        output[section_offset:section_offset + size] = section["data"]
    return bytes(output), {sid: section_offset for sid, section_offset, _size, _count in table}


def _encode_rows(rows):
    count = len(rows)
    head = bytearray(count * 4)
    body = bytearray()
    seen = {}
    for index, row in enumerate(rows):
        offset = seen.get(row)
        if offset is None:
            offset = count * 4 + len(body)
            seen[row] = offset
            cursor = 0
            while cursor < len(row):
                value = row[cursor]
                if value in (0, 255):
                    end = cursor
                    while end < len(row) and row[end] == value and end - cursor < 255:
                        end += 1
                    body.extend((value, end - cursor))
                    cursor = end
                else:
                    body.append(value)
                    cursor += 1
        struct.pack_into("<I", head, index * 4, offset)
    return bytes(head + body)


def self_test():
    info = bytearray(96)
    struct.pack_into("<I", info, 4, 1)
    struct.pack_into("<I", info, 76, 1)
    original_plane = struct.pack("<4f", 0.0, 0.0, 1.0, 0.0)
    bounds = struct.pack("<6f", -1.0, -2.0, -3.0, 1.0, 2.0, 3.0)
    texture = struct.pack("<HHBBHI5I", 4, 4, 1, 0, 0, 0, 16, 0, 0, 0, 0)
    static_prop = bytes(64)
    rows = [bytes((0, 0, 1, 255)), bytes((0, 0, 1, 255))]
    sections = [
        {"id": b"INFO", "data": bytes(info), "count": 1},
        {"id": b"PLAN", "data": original_plane, "count": 1},
        {"id": b"TEXS", "data": texture, "count": 1},
        {"id": b"TXDT", "data": bytes(range(64)), "count": 64},
        {"id": b"SPWN", "data": bytes(16), "count": 1},
        {"id": b"VERT", "data": b"", "count": 0},
        {"id": b"INDX", "data": b"", "count": 0},
        {"id": b"BTCH", "data": b"", "count": 0},
        {"id": b"NODE", "data": b"", "count": 0},
        {"id": b"LEAF", "data": b"", "count": 0},
        {"id": b"PVSZ", "data": _encode_rows(rows), "count": 2},
        {"id": b"BRSH", "data": struct.pack("<III", 0, BOX_BEVELS | 1, 1), "count": 1},
        {"id": b"BSID", "data": struct.pack("<I", 0) + bounds, "count": 1},
        {"id": b"LBRS", "data": b"", "count": 0},
        {"id": b"ENTS", "data": b"", "count": 0},
        {"id": b"EBAT", "data": b"", "count": 0},
        {"id": b"EBRL", "data": b"", "count": 0},
        {"id": b"EOUT", "data": b"", "count": 0},
        {"id": b"SPRP", "data": static_prop, "count": 1},
        {"id": b"SPVZ", "data": _encode_rows(rows), "count": 2},
        {"id": b"PHYS", "data": b"", "count": 0},
        {"id": b"LSTY", "data": b"", "count": 0},
        {"id": b"LSTP", "data": bytes(4096), "count": 64},
        {"id": b"SKYT", "data": struct.pack("<i", -1), "count": 1},
    ]
    source, source_offsets = _pack_sections(sections)
    texture = bytearray(sections[2]["data"])
    struct.pack_into("<I", texture, 8, source_offsets[b"TXDT"])
    struct.pack_into("<I", texture, 12, source_offsets[b"TXDT"] + 16)
    sections[2]["data"] = bytes(texture)
    source, source_offsets = _pack_sections(sections)

    converted, stats = convert_bytes(source)
    output_sections = parse_container(converted, OUTPUT_VERSION, required=())
    ids = {section["id"] for section in output_sections}
    assert struct.unpack_from("<I", converted, 4)[0] == OUTPUT_VERSION
    assert b"PVS " in ids and b"SPVS" in ids
    assert b"PVSZ" not in ids and b"SPVZ" not in ids
    out_brush = by_id(output_sections, b"BRSH")
    first, side_count, _contents = struct.unpack_from("<III", out_brush["data"], 0)
    assert first == 0 and side_count == 7
    out_sides = by_id(output_sections, b"BSID")["data"]
    words = struct.unpack("<7I", out_sides)
    assert words[0] == 0 and all((word & SIDE_BEVEL) for word in words[1:])
    out_planes = by_id(output_sections, b"PLAN")["data"]
    assert len(out_planes) == 7 * 16
    assert by_id(output_sections, b"PVS ")["data"] == rows[0] + rows[1]
    assert by_id(output_sections, b"SPVS")["data"] == rows[0] + rows[1]
    out_offsets, _table, _size = layout_sections(output_sections)
    assert out_offsets[b"TXDT"] == source_offsets[b"TXDT"] + 96
    out_tex = by_id(output_sections, b"TEXS")["data"]
    assert struct.unpack_from("<I", out_tex, 8)[0] == out_offsets[b"TXDT"]
    assert struct.unpack_from("<I", out_tex, 12)[0] == out_offsets[b"TXDT"] + 16
    assert stats["output_bytes"] == len(converted)

    bad_rows = [dict(section) for section in sections]
    bad_rows[10] = dict(bad_rows[10])
    broken = bytearray(bad_rows[10]["data"])
    struct.pack_into("<I", broken, 0, 0xFFFFFFF0)
    bad_rows[10]["data"] = bytes(broken)
    malformed, _ = _pack_sections(bad_rows)
    try:
        convert_bytes(malformed)
    except FormatError:
        pass
    else:
        raise AssertionError("invalid PVSZ row offset was accepted")

    for section_id, payload, count in (
        (b"ENTS", struct.pack("<II", 1, 0x40000000) + bytes(120), 1),
        (b"EOUT", struct.pack("<IiIf", 3, 0, 1, 0.0), 1),
        (b"SPRP", bytes(60) + struct.pack("<I", 1), 1),
    ):
        altered = [dict(section) for section in sections]
        target = next(section for section in altered if section["id"] == section_id)
        target["data"], target["count"] = payload, count
        invalid, _ = _pack_sections(altered)
        try:
            convert_bytes(invalid)
        except FormatError:
            pass
        else:
            raise AssertionError(f"unsupported v6 semantics in {section_id!r} were accepted")

    print("PMAP v6 to PS2 v5 adapter self-test: OK")


def main():
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
        if args.input.resolve() == args.output.resolve():
            raise FormatError("input and output must be different files; the source is never overwritten")
        source = args.input.read_bytes()
        converted, stats = convert_bytes(source)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(converted)
        print(f"PMAP v6 -> PS2 v5: {stats['input_bytes']:,} -> {stats['output_bytes']:,} bytes")
        print(f"Clusters: {stats['clusters']}; TXDT offset: {stats['txdt_offset']}")
        print(f"Output: {args.output}")
        return 0
    except (OSError, FormatError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
