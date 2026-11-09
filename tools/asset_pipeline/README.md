# Asset pipeline

This directory contains host-side tools for inspecting and converting assets before they are loaded by the PS2 runtime.

## Safe bundle inspection

`inspect_bundle.py` reads ZIP archives or individual files without extracting or modifying them. It reports file signatures, sizes, and a few known container identifiers.

```sh
python3 tools/asset_pipeline/inspect_bundle.py path/to/PSRC_657.zip
python3 tools/asset_pipeline/inspect_bundle.py path/to/PSRC_657.zip --json
```

The first inspection of the supplied SandstoneMod PSP bundle found these signatures:

- `PADN`: addon/audio package wrapper; an embedded sub-container identifier is present at offset `0x40`.
- `PSR2`: map bundle (observed version/header word: `0x13`).
- `PSTO`: large store package.
- `PVMD`: viewmodel bundle.
- `IDST`: Source MDL model.
- `VTF\0`: Valve Texture Format.
- `SCRP`, `PSRC`, and `PSND`: embedded identifiers observed inside PADN packages.

These are observations from file headers, not a complete specification. The PADN/PSR2/PSTO/PVMD formats are not yet decoded. The inspector deliberately does not unpack unknown containers or execute bundled code.

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
