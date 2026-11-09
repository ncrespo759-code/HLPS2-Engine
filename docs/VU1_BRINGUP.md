# VU1 bring-up plan

## Current verified state

- The EE bootstrap initializes the GS and draws the rotating CPU-side cube.
- `dvp-as` assembles `ps2/src/vu1_probe.vsm`; its `.vudata` symbols are linked into `hlps2.elf`.
- The current probe is a terminating NOP program. It is **not uploaded to VU1 or executed**.
- Keep the CPU cube intact until a separate VU1-rendered primitive is visibly verified in PCSX2 and, later, on SCPH-90001 hardware.

## Required VU1 execution sequence

VU1 has private micro-memory and data memory. The EE communicates with it through VIF1; a VU1 program can submit its output to the GS through GIF PATH1 using `XGKICK`.

The runtime path should be implemented in isolated stages:

1. Initialize DMA channel VIF1 independently from the existing GIF channel.
2. Build a correctly aligned VIF1 DMA packet that uploads the assembled microprogram with the VIF `MPG` command.
3. Upload a small, fixed input block to VU1 data memory using `UNPACK`.
4. Start the program with `MSCAL` at its VU micro-memory address.
5. Wait for VIF1/VU1 completion using the appropriate VIF flush/fence before reusing packet or input memory.
6. Only after the execution-only test is stable, make the program emit a GS packet with `XGKICK` and verify a visible primitive.
7. Keep the CPU cube as the fallback while comparing output and timing.

## VIF commands relevant to this path

- `MPG` (`0x4A`): uploads microinstructions to VU micro-memory.
- `UNPACK` (command family `0x60+`): transfers vertex/input data to VU data memory.
- `MSCAL` (`0x14`): starts a microprogram at the specified instruction address.
- `FLUSHE` (`0x10`): waits for VU execution to finish.
- `FLUSH` (`0x11`): additionally waits for PATH1/PATH2 transfers to finish.
- `FLUSHA` (`0x13`): stronger VIF1 synchronization, including pending PATH3 requests.

PS2SDK provides packet2 helpers such as `packet2_vif_add_micro_program`, `packet2_vif_mscal`, `packet2_vif_flush`, and UNPACK helpers. Prefer these helpers if the project adopts packet2; otherwise document and test every manually encoded VIF word and alignment rule.

## Safety and correctness rules

- Do not assume a successful `dvp-as` build proves runtime execution.
- Do not overwrite VU1 micro-memory while a program is running.
- Do not reuse DMA source buffers until the relevant DMA/VIF completion has been observed.
- Keep VIF1 and GIF DMA initialization/waits separate; do not change the working GIF path as part of this test.
- Respect VIF MPG limits and split larger microprogram uploads into legal chunks.
- Keep the first VU1 test deterministic: fixed input, fixed output, no textures, no game assets, no dynamic allocation.
- A successful CI build is only a build milestone. Runtime success requires a visible PCSX2 result and explicit confirmation.

## References

- PS2SDK VIF command definitions and packet helpers:
  - https://ps2dev.github.io/ps2sdk/group__packet2__vif.html
  - https://ps2dev.github.io/ps2sdk/vif__codes_8h.html
  - https://ps2dev.github.io/ps2sdk/dma_8h.html
- PS2 VIF/VU1 hardware behavior:
  - https://israpps.github.io/ps2tek/
  - https://docs.alexrp.com/mips/ee_vu.pdf
- Practical VU1 rendering sequence and PATH1/XGKICK example:
  - https://glampert.github.io/2016/01-22/q2ps2-hardware-accelerated-vertex-xform/

These references inform the implementation plan; this document does not claim that the project has implemented or verified VU1 execution.
