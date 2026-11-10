# Asset pipeline

This directory contains host-side tools for inspecting and converting assets before they are loaded by the PS2 runtime.

## Safe bundle inspection

`inspect_bundle.py` reads ZIP archives or individual files without extracting or modifying them. It reports file signatures, sizes, and a few known container identifiers.

~~~sh
python3 tools/asset_pipeline/inspect_bundle.py path/to/PSRC_657.zip
python3 tools/asset_pipeline/inspect_bundle.py path/to/PSRC_657.zip --json
~~~

The first inspection of the supplied SandstoneMod PSP bundle found these signatures:

- `PADN`: addon/audio package wrapper; an embedded sub-container identifier is present at offset `0x40`.
- `PSR2`: map bundle (observed version/header word: `0x13`).
- `PSTO`: large store package.
- `PVMD`: viewmodel bundle.
- `IDST`: Source MDL model.
- `VTF\0`: Valve Texture Format.
- `SCRP`, `PSRC`, and `PSND`: embedded identifiers observed inside PADN packages.

These are observations from file headers, not a complete specification. The PADN/PSR2/PSTO/PVMD formats are not yet decoded. The inspector deliberately does not unpack unknown containers or execute bundled code.

## BSP header inspection

`inspect_bsp.py` checks map headers and lump ranges without extracting or modifying the map:

- Source 1: `VBSP`, versions 19-21, 64 lumps.
- GoldSrc: version 30, 15 lumps.
- Other versions and malformed/out-of-range lumps are rejected.
- The report can be printed as text or JSON.

~~~sh
python3 tools/asset_pipeline/inspect_bsp.py path/to/map.bsp
python3 tools/asset_pipeline/inspect_bsp.py path/to/map.bsp --json
python3 tools/asset_pipeline/inspect_bsp.py --self-test
~~~

Half-Life: Source is a Source 1 game, so its maps should use the Source VBSP path when their actual header is in the supported range. Original Half-Life and Counter-Strike 1.6 GoldSrc maps use the separate GoldSrc path. The header alone cannot identify which Source game produced a map; matching game files and materials are still required.

This is a header/range inspector, not a BSP geometry parser or converter. See `docs/BSPCONV_PORT_PLAN.md` for the audit of the reference converter and the PMAP v5/v6 incompatibility.

## Conversion pipeline

The intended workflow is:

1. Inspect user-supplied Source/GoldSrc assets and platform-specific bundles.
2. Validate headers, offsets, counts, compression and bounds before parsing.
3. Extract only documented or fully understood data.
4. Convert supported assets into compact, versioned PS2 runtime formats.
5. Emit a report listing converted, reduced, and unsupported features.

Initial conversion targets:

- Source and GoldSrc BSP inspection/conversion.
- MDL/VVD/VTX model inspection and mesh/animation reduction.
- VTF/VMT texture extraction and PS2 texture conversion.
- Audio extraction and conversion for the eventual IOP audio backend.
- SandstoneMod bundle research, starting with read-only format identification.

## Platform boundary

The supplied SandstoneMod archive is a PSP game package, not a PS2 port or a Half-Life 2 engine source tree. Its PSP executable/module files (`EBOOT.PBP`, `*.prx`) are not usable as PS2 executables. Its Source-format assets may be useful after validation and conversion. No proprietary game assets or PSP engine binaries are copied into this repository.

## First PS2 texture conversion step

`vtf_to_hlps2.py` converts a deliberately limited, validated subset of VTF textures into the host-side `H2TX` container:

- VTF 7.0-7.2, one frame, one 2D image (no cubemaps or volume textures).
- RGBA8888, ABGR8888, RGB888, BGR888, BGRA8888 and DXT1 source pixels.
- Output pixels are linear little-endian RGBA5551 (GS PSMCT16), with a 20-byte `H2TX` header. The PS2 runtime upload path is a separate task.
- Unsupported formats/layouts fail with an explicit error; the source file is never modified.

Run:

~~~sh
python3 tools/asset_pipeline/vtf_to_hlps2.py input.vtf output.h2tx
python3 tools/asset_pipeline/vtf_to_hlps2.py --self-test
~~~

This converter is the first texture-format milestone, not proof that a texture from a game asset pack has been imported or displayed on the PS2 yet.

## First model inspection step

`inspect_idst.py` validates the common Source `IDST` MDL header and reports its version, checksum, model name and declared file length. It also lists the matching `.vvd` and `.dx90.vtx` companion filenames to look for.

~~~sh
python3 tools/asset_pipeline/inspect_idst.py path/to/model.mdl --json
python3 tools/asset_pipeline/inspect_idst.py --self-test
~~~

This is header validation only. It does not claim to convert or render the model; mesh decoding and PS2-friendly reduction follow after the exact model and its companion files are identified.

## Asset pack inventory

`scan_source_assets.py` scans a folder or ZIP without extracting it. It groups `.mdl` files with matching `.vvd` and `.dx90.vtx` (or `.vtx`) companions, and lists `.vtf`/`.vmt` textures. It does not decode model meshes or trust asset contents.

~~~sh
python3 tools/asset_pipeline/scan_source_assets.py path/to/asset-pack.zip
python3 tools/asset_pipeline/scan_source_assets.py path/to/extracted-assets --json
python3 tools/asset_pipeline/scan_source_assets.py --self-test
~~~
