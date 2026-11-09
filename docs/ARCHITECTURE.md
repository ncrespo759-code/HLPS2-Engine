# Architecture notes

## Target constraints

- PlayStation 2 Emotion Engine (EE), Vector Units (VU0/VU1), Graphics Synthesizer (GS), IOP and 32 MB main RAM.
- Every subsystem must have an explicit memory budget. Avoid allocating large transient buffers from the 32 MB heap.
- Prefer streaming, compact runtime formats, fixed-size pools and predictable ownership.

## Runtime layers

1. Platform: boot, memory map, timers, controller, file/device I/O and diagnostics.
2. Resource system: handles, bounded caches, streaming and converted asset formats.
3. World: BSP-derived static geometry, visibility, collision and entity state.
4. Renderer: EE builds batches, VU1 transforms/lighting/clipping where appropriate, GS consumes display lists.
5. Audio: IOP-side playback/mixing strategy to be evaluated against available PS2SDK modules.

## Renderer decision

The target direction is a native EE/VU1/GS renderer. The old PS2-GMOD implementation is useful as a reference for VU1 workloads and PS2 project layout, but its gsKit dependency is not adopted as a requirement. First establish a minimal GS display path, then benchmark VU1 microprograms and DMA/display-list submission.

## Asset conversion

Source assets are not runtime-ready for PS2. Host tools should inspect inputs and emit bounded, documented formats:
- BSP: retain only required world geometry, visibility and collision data.
- Models: reduce mesh complexity, bone count, animation data and texture resolution.
- Textures: convert to PS2-supported swizzled/paletted or suitable direct-color layouts.
- Audio: resample and encode to a format supported by the chosen IOP playback path.

Conversion must be deterministic and report unsupported features instead of silently dropping them.
