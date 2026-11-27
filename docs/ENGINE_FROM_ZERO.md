# HLPS2: arquitectura desde cero

## Objetivo

Crear un motor nativo para Half-Life 1 en PlayStation 2, sin portar el motor de Nintendo 64 ni reutilizar Xash3D como base. Los recursos originales del juego deberán convertirse a formatos propios y compactos; no se redistribuyen assets de Valve.

## Hardware objetivo

- EE/R5900: lógica principal, mundo, entidades y preparación de render.
- VU0: apoyo matemático y transformaciones cuando las mediciones lo justifiquen.
- VU1: transformación y preparación de lotes geométricos.
- GS: rasterización, framebuffer, texturas y depth.
- DMA/VIF/GIF: transferencia de datos y comandos con sincronización explícita.
- IOP: mandos, audio y dispositivos a través de interfaces PS2SDK.

No se declara que todo el render vaya a VU0/VU1 desde el primer día. Se medirá cada etapa y se mantendrá una ruta de depuración EE.

## Presupuesto inicial

La consola tiene 32 MiB de RAM principal compartida por código, heap, mapas y buffers. El presupuesto definitivo se fijará con mediciones; ningún subsistema podrá asumir memoria ilimitada. Los recursos se cargarán por bloques y los pools tendrán límites explícitos.

## Orden de implementación

1. Core portable: tipos, arena allocator, logging y reloj.
2. Plataforma EE: arranque, memoria, pad y lectura de archivos.
3. Renderer mínimo: framebuffer GS y triángulo, luego texturas y profundidad.
4. Geometría: buffers EE -> VIF1/VU1 -> GIF/GS, con fences y doble buffer.
5. Formato de mapa convertido: parser validado, límites de tamaño, visibilidad y colisión.
6. Entidades, movimiento, armas, NPC y audio.
7. Integración de contenido GoldSrc legalmente obtenido por el usuario.

## Criterio de aceptación

Un ELF que solo arranca no es un motor jugable. Cada fase tendrá pruebas automatizadas y una lista de pruebas en consola real. La primera meta visual será una escena de prueba estable; después se cargará un mapa pequeño convertido.

## Exclusiones

- No usar el repositorio ToxyCola/Half-Life-Nintendo-64-Port como dependencia ni referencia de código.
- No importar RSP/RDP, LibDragon ni Tiny3D.
- No depender de conexión a Internet.
- No incorporar parches antiguos sin revisión aislada.
