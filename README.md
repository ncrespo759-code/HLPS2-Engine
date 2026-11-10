# HLPS2-Engine

**Objetivo actual:** desarrollar un sandbox 3D para PlayStation 2 inspirado en la experiencia de Garry's Mod y en las referencias PS2-GMOD y Retcon's Mod. Es una implementación independiente: no es un port oficial de Garry's Mod, no ejecuta el motor PSP y no contiene código ni recursos propietarios de Valve.

## Experiencia prevista

- Cargar mapas de Source 1 (incluidos los de Half-Life: Source) y GoldSrc mediante herramientas de conversión en PC.
- Explorar mapas y crear construcciones con props, físicas y restricciones.
- Incorporar herramientas de construcción, NPCs, ragdolls y armas por etapas.
- Evaluar multijugador LAN después de estabilizar el motor, la memoria y la carga de mapas.
- Mantener todo dentro de los 32 MB de RAM de PS2, con recursos reducidos y formatos de runtime propios/documentados.

Estas son metas, no funciones ya implementadas.

## Estado real del proyecto (10-11-2026)

- La base de PS2SDK compila en GitHub Actions.
- El ELF estable dibuja un cubo 3D rotatorio con transformaciones en EE/CPU.
- Hay pruebas separadas de carga VU1 y de envío VU1 → GS mediante XGKICK. La prueba del triángulo todavía recibe del EE el paquete GS ya construido: **no demuestra transformación de vértices en VU1**.
- Todavía no hay cargador de mapas, motor de físicas sandbox, sistema de props, NPCs, audio ni multijugador jugable.
- El pipeline host-side ya inspecciona inventarios de modelos Source y convierte un subconjunto de VTF; la conversión BSP para PS2 está pendiente.

La ejecución 63 de GitHub Actions pasó el 9 de noviembre de 2026 y compiló los tres ELF de prueba. Eso valida la compilación, no el arranque de un sandbox completo en una PS2 real.

## Referencias técnicas

- [retcon26/PS2-GMOD](https://github.com/retcon26/PS2-GMOD): referencia principal para arquitectura PS2, carga de mapas, memoria, input DualShock 2, audio IOP, filesystem de disco y renderizado con VU1. Su implementación actual usa una capa compatible con PSP-GU sobre gsKit; se estudia como referencia, no se copia automáticamente.
- [retcon26/retcons-mod](https://github.com/retcon26/retcons-mod): referencia principal para el conversor host-side de mapas Source/GoldSrc, modelos MDL/VVD/VTX, materiales VMT/VTF, colisión, props y NPCs. El conversor actual genera PMAP v6, por lo que no es compatible directamente con el runtime PS2-GMOD antiguo que exige PMAP v5.

Los repositorios de referencia no muestran una licencia declarada en sus metadatos ni un archivo LICENSE en sus árboles actuales. Por eso este proyecto documenta los formatos y desarrolla adaptadores independientes; no copia archivos de código de esos repositorios sin autorización/licencia compatible.

## Arquitectura prevista

| Área | Responsabilidad |
|---|---|
| `ps2/` | Arranque PS2SDK, EE, DMA, VIF1/VU1, GS, IOP y DualShock 2 |
| `engine/` | Memoria, recursos, escena, entidades, física y lógica sandbox |
| `renderer/` | Backend EE/VU1/GS, lotes, materiales, visibilidad y clipping |
| `tools/asset_pipeline/` | Inspección y conversión host-side de BSP, MDL/VVD/VTX, VTF/VMT y audio |
| `docs/` | Formatos de runtime, límites de memoria y decisiones técnicas |

## Plan de trabajo

1. **Fundación:** build PS2SDK, ELF de prueba y CI reproducible.
2. **Assets:** inspeccionar BSP Source/GoldSrc y modelos; convertirlos a formatos PS2 acotados.
3. **Runtime de mapas:** cargar geometría, texturas, visibilidad y colisión con validación de límites.
4. **Renderer:** mantener el cubo EE como fallback; completar una prueba VU1 que transforme vértices reales y después integrar lotes de mapas.
5. **Sandbox:** props, físicas simples, herramientas y entidades; NPCs/ragdolls después de medir RAM y rendimiento.
6. **Plataforma:** audio IOP, input y filesystem; LAN solo cuando el juego local sea estable.

## Compilar

Con PS2SDK instalado y `PS2SDK` apuntando a su directorio:

~~~sh
make -C ps2
~~~

El workflow de GitHub Actions comprueba la toolchain y genera los ELF de prueba como artefactos. Un build correcto no equivale a una prueba en hardware.

## Recursos y seguridad

No se suben mapas, modelos, sonidos ni texturas propietarios. Los recursos deben proceder de instalaciones legítimas del usuario y convertirse localmente. No se reutilizan parches antiguos de Xash3D ni ELFs que hayan provocado pantallas negras, cuelgues o retornos al navegador de Memory Card.
