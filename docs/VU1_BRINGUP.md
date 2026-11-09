# VU1 bring-up plan

## Verified state (2026-11-09)

- The stable `hlps2.elf` initializes the GS and draws the rotating 3D cube. Its vertex transform, projection, face culling and painter sorting are still CPU/EE-side.
- `hlps2-vu1-test.elf` uploads and starts an isolated VU1 microprogram. The user confirmed the VU1 probe completion message in PCSX2.
- `hlps2-vu1-triangle-test.elf` uploads a prebuilt six-qword GIF packet into VU1 data memory. The VU1 microprogram executes `XGKICK`; the user confirmed the cyan triangle and the diagnostic text are visible.
- Important limitation: the triangle test does **not** transform vertices. The EE prebuilds the final GS packet, and VU1 only forwards it to the GS.
- GitHub Actions run #62 passed all asset-pipeline self-tests and built/verified the stable cube ELF, isolated VU1 test ELF, and VU1-to-GS triangle ELF.

Keep the cube and current triangle ELF as known-good reference tests. New VU1 geometry work must be a separate target until it is visibly confirmed in PCSX2.

## Next milestone: VU1 transforms three vertices

The next test should be a separate `hlps2-vu1-transform-test.elf`:

1. EE initializes VIF1 and uploads a small VU1 microprogram with the PS2SDK packet2 MPG helper.
2. EE UNPACKs three source vertices and a compact transform/projection constant block into VU1 data memory.
3. VU1 loads the vertices, performs an actual vector transform and perspective projection, converts screen coordinates to GS fixed-point format, and writes a packed GIF packet in VU1 data memory.
4. VU1 sends that generated packet to the GS with `XGKICK`.
5. The visible output must change when the EE changes the input rotation angle. The EE must not precompute the final screen-space XYZ coordinates or build the final GIF packet.
6. Keep a fixed-angle mode first for deterministic validation; add animation only after the fixed output is correct.

A successful assembler/linker run is not runtime proof. Confirm the changed geometry visually in PCSX2 before calling this milestone complete.

## Reference implementation notes

The separate `retcon26/PS2-GMOD` project contains useful VU1 renderer architecture in `ps2/vu1_map.vsm`, `ps2/vu1_lit.vsm`, and `ps2/gu.c`. Its map path demonstrates a practical data layout:

- A matrix/constants block at the beginning of VU1 data memory.
- A GIF tag and primitive metadata prepared for the output stream.
- Input vertex data in a separate region so VU1 output does not overwrite input still being read.
- VU1 vector instructions perform transform/projection and write ST/RGBAQ/XYZ data.
- A final `XGKICK` submits the VU-generated GIF packet.

Use this as an architectural reference only. Do not copy the PSP game engine, PSP SDK, or its asset/runtime assumptions into HLPS2-Engine. The HLPS2 implementation must use PS2SDK VIF1/VU1/GS interfaces and preserve the existing working tests.

## VIF/VU1 rules

- `MPG` uploads VU microinstructions; `UNPACK` uploads data; `MSCAL` starts a microprogram.
- `FLUSHE` waits for VU execution; `FLUSH` additionally waits for PATH1/PATH2 transfers; use the synchronization level required before reusing buffers.
- Respect VU1's micro-memory and data-memory limits and MPG transfer limits.
- Keep VIF1 and GIF DMA synchronization separate.
- Do not overwrite VU1 micro-memory or data buffers while VU1/GIF is consuming them.
- The EE must not build the final output GIF packet in the transform test; otherwise the test would only repeat the current forwarding test.

## Asset pipeline status

Host-side VTF conversion and Source MDL header/inventory checks are separate from rendering. They do not yet mean Source models or textures are loaded by the PS2 runtime. Actual asset conversion requires the original asset ZIP and matching model companion files where applicable.

## References

- PS2SDK VIF packet helpers: https://ps2dev.github.io/ps2sdk/group__packet2__vif.html
- PS2SDK VIF command definitions: https://ps2dev.github.io/ps2sdk/vif__codes_8h.html
- PS2 hardware notes: https://israpps.github.io/ps2tek/
- VU1 rendering architecture reference: https://github.com/retcon26/PS2-GMOD/blob/main/ps2/vu1_map.vsm
