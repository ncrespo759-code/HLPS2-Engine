# HLPS2-Engine

Proyecto para desarrollar un motor nativo de Half-Life 1 para PlayStation 2, desde cero.

La nueva línea de trabajo está en la rama ps2-engine-from-zero. No usa como base el port de Nintendo 64 ni Xash3D. Los prototipos anteriores quedan aislados y no se consideran parte del motor nuevo.

## Plataforma

- Emotion Engine / R5900 para lógica y preparación de escena.
- VU0/VU1 para trabajo vectorial y geometría, según mediciones.
- GS para rasterización.
- DMA, VIF y GIF para transferencias.
- 32 MiB de RAM principal: pools y presupuestos explícitos.

## Estado

La primera implementación nueva es un núcleo portable con un asignador lineal acotado, sin dependencia de malloc. Todavía no es un motor jugable ni contiene mapas, modelos o recursos de Valve.

## Estructura nueva

- engine/core/: núcleo portable.
- engine/tests/: pruebas ejecutables en PC.
- docs/ENGINE_FROM_ZERO.md: arquitectura y fases.
- ps2/: prototipos de plataforma anteriores, aislados del core nuevo.

## Pruebas del core

Desde la carpeta engine:

    make test

## Objetivo inmediato

Validar el core y después crear el arranque EE limpio, seguido por un framebuffer GS de prueba. Un ELF que solo arranca no se considerará una versión funcional de Half-Life.

No se incluyen assets propietarios. Los recursos deberán ser aportados por el usuario y convertidos a formatos compatibles con PS2.
