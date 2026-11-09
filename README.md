# HLPS2-Engine

**Objetivo:** desarrollar desde cero una base de motor para ejecutar una experiencia compatible con **Half-Life 2 en PlayStation 2**. Este repositorio es el proyecto PS2; no es un port de Garry's Mod ni una copia del motor PSP.

> Estado actual: fundación del proyecto. El primer ELF es una prueba de arranque del entorno PS2SDK, no un motor jugable ni una implementación de Half-Life 2.

## Principios

- Diseñar para la PlayStation 2 real: Emotion Engine (EE), Vector Units (VU0/VU1), Graphics Synthesizer (GS), 32 MB de RAM principal y almacenamiento limitado.
- Separar el código común del código específico de PS2.
- Priorizar un renderizador propio EE/VU1/GS. GSKit queda como referencia/compatibilidad opcional, no como dependencia arquitectónica obligatoria.
- No copiar el motor PSP de Retcon's Mod. Estudiar sus herramientas de conversión y formatos compactos, adaptándolos a PS2.
- No importar mecánicas sandbox, Lua, ragdolls ni multiplayer por defecto: solo se incorporarán si aportan al objetivo HL2 y caben en PS2.
- Mantener builds reproducibles en GitHub Actions y no reutilizar parches/ELF de pruebas anteriores sin validarlos.

## Referencias técnicas

- [retcon26/retcons-mod](https://github.com/retcon26/retcons-mod): referencia de pipeline de assets. Interesan los conceptos de lectura/conversión de BSP Source y GoldSrc, VPK/VTF/VMT, MDL/VVD/VTX, texturas paletizadas, audio y datos reducidos.
- [retcon26/PS2-GMOD](https://github.com/retcon26/PS2-GMOD): referencia de arquitectura PS2 antigua, organización EE/PS2 y uso de VU1 para geometría. Su implementación usa gsKit; se estudiará, no se copiará automáticamente.

## Arquitectura prevista

| Área | Responsabilidad |
|---|---|
| `ps2/` | Arranque y plataforma PS2 (EE, DMA, VU, GS, IOP) |
| `engine/` | Sistemas comunes: memoria, recursos, escena, entidades y tiempos |
| `renderer/` | Backend PS2: preparación EE, microprogramas VU1 y comandos GS |
| `tools/` | Herramientas host-side para inspeccionar y convertir assets |
| `docs/` | Especificaciones, decisiones y límites del port |

## Plan de trabajo

1. **Fundación:** build PS2SDK, ELF de prueba y CI.
2. **Plataforma:** memoria, logging, pad, temporización y lectura desde dispositivo.
3. **Assets:** inspección y conversión incremental de BSP/MDL/texturas/audio; nunca cargar recursos Source originales sin adaptar.
4. **Render:** triángulos, texturas, depth, materiales simples; después VU1 y optimización.
5. **Mundo:** BSP convertido, visibilidad, colisión y entidades.
6. **Gameplay:** sistemas necesarios para una demo HL2 reducida.

## Compilar

Con PS2SDK instalado y `PS2SDK` apuntando a su directorio:

```sh
make -C ps2
```

El workflow de GitHub Actions comprueba la toolchain y genera `hlps2.elf` como artefacto. El éxito de compilación no significa todavía que el ELF haya sido probado en una consola.

## Licencia y recursos

No se incluyen assets propietarios de Valve. Los mapas, modelos, sonidos y texturas deberán proceder de instalaciones legítimas del usuario y convertirse a formatos adecuados para PS2. La licencia del código se definirá antes de distribuir builds.
