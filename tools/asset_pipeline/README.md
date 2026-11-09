# Asset pipeline (planned)

This directory is reserved for host-side tools. The intended workflow is:

1. Read user-supplied Source/GoldSrc assets.
2. Validate headers, offsets, counts and bounds before parsing.
3. Produce compact PS2 runtime data with explicit versioning.
4. Emit a conversion report listing dropped or unsupported features.

Initial targets, inspired by the useful parts of retcon26/retcons-mod:
- Source and GoldSrc BSP inspection/conversion.
- MDL family inspection and mesh/animation reduction.
- VTF/VMT texture extraction and PS2 texture conversion.
- Audio extraction and conversion for the eventual IOP audio backend.

No proprietary game assets or copied PSP engine code are stored here. A converter is not implemented yet; this file records scope only.
