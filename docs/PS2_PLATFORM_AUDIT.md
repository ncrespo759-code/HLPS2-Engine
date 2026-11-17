# Auditoría de plataforma PS2: referencia PS2-GMOD

**Fecha de revisión:** 17-11-2026  
**Referencia:** retcon26/PS2-GMOD (versión declarada 1.3.0)  
**Proyecto objetivo:** ncrespo759-code/HLPS2-Engine

Este documento registra lo que se observó en el código de referencia y separa claramente lo existente en PS2-GMOD de lo implementado en HLPS2-Engine. No implica que se haya copiado o integrado código del repositorio externo.

## 1. Renderer GS/VU1

PS2-GMOD utiliza una capa de estilo PSP-GU sobre gsKit. La geometría del mapa se prepara en el EE y se envía por VIF1 a VU1. El microprograma de mapa transforma, proyecta, aplica niebla, hace culling y genera paquetes GIF que VU1 entrega al GS con XGKICK.

Observaciones concretas:
- Los vértices de mapa usan registros compactos de 16 bytes.
- VU1 procesa hasta 33 triángulos por buffer de trabajo.
- La ruta VIF1 ordena el trabajo de VU1 (PATH1) y los paquetes DIRECT del EE (PATH2); el código sincroniza con FLUSH antes de cambiar estado GS cuando todavía puede haber geometría en vuelo.
- Si una caja de lote cruza el plano cercano o sale del guard band, el clipping vuelve a la CPU.
- Hay otro microprograma VU1 para props, NPCs, ragdolls y el arma en primera persona.
- El código de referencia reserva una arena de scratch de 1 MB y comenta que quedan aproximadamente 2 MB de GS memory para texturas después de los framebuffers; limita texturas de runtime a 256 px.

**Estado HLPS2-Engine:** el cubo EE sigue siendo el fallback estable. Existen ELFs separados de prueba VU1 y VU1→GS, pero el triángulo de prueba recibe del EE el paquete GIF final. Todavía no demuestra transformación de vértices en VU1. No se debe reemplazar el cubo hasta que un test independiente de transformación real se vea en PCSX2.

## 2. Memoria principal: 32 MB

PS2-GMOD selecciona recursos de detalle bajo para PS2: mapas, props, NPCs y sonidos tienen variantes reducidas. El cargador intenta elegir el mapa apropiado y puede recurrir al archivo .low cuando el mapa completo no cabe. También mide el bloque libre más grande para informar fallos de asignación.

Decisiones para HLPS2-Engine:
- Tratar 32 MB como presupuesto total, no como memoria disponible para el mapa.
- Medir heap libre y bloque contiguo antes de cargar recursos grandes.
- Reservar por separado memoria de programa, buffers DMA/VIF, texturas/VRAM y datos de escena.
- Mantener un presupuesto de mapa low y rechazar counts/offsets que excedan límites antes de reservar.
- El exportador PMAP añadido a esta rama exige INFO.tier = 0 (low, 32 MB).

El número de memoria libre de PS2-GMOD no debe copiarse como constante: depende del ELF, buffers y módulos IOP que se carguen.

## 3. Audio e IOP

La referencia usa audsrv como salida al IOP:
- salida estéreo PCM de 16 bits a 22050 Hz;
- mezclador de 16 voces;
- bloques de 512 frames estéreo;
- hilo de mezcla separado y sincronización con semáforo;
- paquete de audio low a 16 kHz para ahorrar varios MB frente al paquete de 44.1 kHz.

**Estado HLPS2-Engine:** no hay backend de audio integrado. Antes de añadirlo hay que definir formato de paquete, límite de voces, memoria máxima y ciclo de vida del hilo; no cargar todos los sonidos en RAM sin presupuesto.

## 4. Input DualShock 2

La referencia usa libpad:
- configura el mando en modo DualShock analógico y bloquea el modo para evitar que el botón Analog desactive los sticks;
- zona muerta observada de 0,2;
- stick izquierdo para movimiento y derecho para mirar;
- botones del mando mapeados a acciones del motor compartido.

**Estado HLPS2-Engine:** todavía no hay sistema de input de juego. El siguiente backend debe ser PS2 nativo con lectura de estado estable, calibración/deadzone y mapeo configurable; no debe depender de la capa PSP.

## 5. Filesystem y paquetes

PS2-GMOD usa un archivo P2PK porque ISO9660 no resuelve bien nombres largos de recursos:
- cabecera de 16 bytes;
- entradas de directorio de 64 bytes, con ruta de 52 bytes y offset/tamaño de 32 bits;
- payloads alineados a 2048 bytes;
- DATA.PAK, DATA1.PAK, etc., separados por debajo de 2 GB para evitar límites de seek de 32 bits;
- el lector de referencia admite hasta ocho partes y busca en CD/DVD, host filesystem o memory card.

**Estado HLPS2-Engine:** no hay filesystem de runtime ni cargador PMAP. Se recomienda un contenedor propio y versionado con validación de límites, rutas normalizadas, lectura parcial y archivos divididos; no depender de nombres 8.3 ni asumir que el mapa completo debe cargarse de una sola vez.

## 6. Build y dependencias

PS2-GMOD compila con PS2SDK, gsKit y dvp-as. Su build.sh separa el objetivo ELF del empaquetado completo: el build de ISO también requiere Python/Pillow y datos ya convertidos por las herramientas del proyecto PSP.

**Estado HLPS2-Engine:** el workflow actual usa la imagen ps2dev, configura compilador EE y dvp-as, ejecuta pruebas host-side y compila tres ELFs de diagnóstico. Todavía no integra gsKit, audsrv, libpad, DEV9 ni el filesystem P2PK. La compilación CI no equivale a arranque real en PS2.

## 7. Orden recomendado de integración

1. Completar un test VU1 que transforme tres vértices reales, sin que el EE prepare coordenadas finales ni el paquete GIF.
2. Implementar un lector de contenedor/PMAP con validación estricta de offsets, counts, alineación y memoria.
3. Añadir input DualShock 2 y temporización en una prueba aislada.
4. Añadir filesystem de paquetes con lectura parcial y fallback de bajo detalle.
5. Integrar audio IOP con presupuesto fijo de voces y memoria.
6. Recién después, conectar mapas, colisión y props; LAN queda para cuando el modo local sea estable.

## Referencias de código consultadas

- PS2-GMOD: ps2/gu.c, ps2/vu1_map.vsm, ps2/vu1_lit.vsm, ps2/audio.c, ps2/input.c, ps2/pakfs.c, engine/map.c, engine/collision.c y build.sh.
- Retcon's Mod: tools/bspconv/bsp.py, goldsrc.py, convert.py, models.py, collision.py, pmap.py y psp/src/pmap_format.h.

No se incorporó código ni contenido propietario de esos repositorios.