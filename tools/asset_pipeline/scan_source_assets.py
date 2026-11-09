#!/usr/bin/env python3
"""Inventory Source models and textures in a folder or ZIP without extracting it."""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath


MODEL_EXTS = {".mdl", ".vvd", ".vtx"}
TEXTURE_EXTS = {".vtf", ".vmt"}


def inventory(names: list[str]) -> dict:
    files = [n.replace("\\", "/") for n in names if n and not n.endswith("/")]
    by_lower = {n.lower(): n for n in files}
    models = []
    textures = []
    for name in sorted(files, key=str.lower):
        path = PurePosixPath(name)
        ext = path.suffix.lower()
        stem = str(path.with_suffix("")).lower()
        if ext == ".mdl":
            companions = {
                "vvd": by_lower.get(stem + ".vvd"),
                "vtx": by_lower.get(stem + ".dx90.vtx") or by_lower.get(stem + ".vtx"),
            }
            models.append({
                "mdl": name,
                "vvd": companions["vvd"],
                "vtx": companions["vtx"],
                "ready_for_mesh_inspection": all(companions.values()),
            })
        elif ext in TEXTURE_EXTS:
            textures.append(name)
    return {
        "file_count": len(files),
        "model_count": len(models),
        "complete_model_sets": sum(1 for m in models if m["ready_for_mesh_inspection"]),
        "incomplete_model_sets": sum(1 for m in models if not m["ready_for_mesh_inspection"]),
        "texture_count": len(textures),
        "models": models,
        "textures": textures,
    }


def scan(path: Path) -> dict:
    if path.is_dir():
        names = [p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()]
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"ZIP CRC check failed at {bad}")
            names = archive.namelist()
    else:
        raise ValueError("input must be a directory or a valid ZIP archive")
    result = inventory(names)
    result["source"] = str(path)
    return result


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        archive_path = Path(temp) / "assets.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("models/props/crate.mdl", b"IDST")
            archive.writestr("models/props/crate.vvd", b"")
            archive.writestr("models/props/crate.dx90.vtx", b"")
            archive.writestr("models/props/missing.mdl", b"IDST")
            archive.writestr("materials/props/crate.vtf", b"VTF\\0")
            archive.writestr("materials/props/crate.vmt", b"")
        result = scan(archive_path)
        assert result["model_count"] == 2
        assert result["complete_model_sets"] == 1
        assert result["incomplete_model_sets"] == 1
        assert result["texture_count"] == 2
    print("Source asset inventory self-test: OK")


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
        result = scan(args.input)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Files: {result['file_count']}")
            print(f"Models: {result['model_count']} ({result['complete_model_sets']} complete model sets)")
            print(f"Textures: {result['texture_count']}")
            for model in result["models"]:
                state = "complete" if model["ready_for_mesh_inspection"] else "missing VVD/VTX"
                print(f"MODEL [{state}] {model['mdl']}")
            for texture in result["textures"]:
                print(f"TEXTURE {texture}")
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
