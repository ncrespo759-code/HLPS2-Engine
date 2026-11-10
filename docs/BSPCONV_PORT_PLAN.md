# Auditoría del conversor BSP para el sandbox PS2

**Fecha:** 10 de noviembre de 2026  
**Objetivo:** determinar qué puede reutilizarse conceptualmente de tools/bspconv y qué falta para que los mapas lleguen a un runtime de PlayStation 2.

## Repositorios y revisiones inspeccionadas

- Proyecto propio: ncrespo759-code/HLPS2-Engine, commit a46b33b7e30e.
- Referencia PS2: retcon26/PS2-GMOD, commit 646027c3730c.
- Referencia del conversor: retcon26/retcons-mod, commit 99fe6c485df6.

No se modificó ninguno de los repositorios de referencia.

## Resultado principal: Half-Life: Source

**Sí, el formato de mapa de Half-Life: Source entra en la ruta Source BSP del conversor, siempre que el archivo concreto tenga cabecera VBSP y versión 19, 20 o 21.** Half-Life: Source usa Source 1; no debe confundirse con los mapas originales de Half-Life/Counter-Strike 1.6 en GoldSrc.

El conversor distingue así:

- Source 1: firma VBSP, 64 entradas de lump y versiones admitidas 19-21 en tools/bspconv/bsp.py.
- GoldSrc: versión 30 y 15 lumps en tools/bspconv/goldsrc.py.

tools/bspconv/convert.py selecciona GoldSrcBsp cuando is_goldsrc() reconoce la versión 30; en los demás casos intenta el parser Source Bsp. Para mapas Half-Life: Source, por tanto, se debe usar la ruta VBSP, no la ruta GoldSrc.

Hay además dos indicios específicos en el conversor:
- FULL_RES_GAMES incluye hl1, hl1mp, valve, gearbox y bshift.
- content_dirs_for() lee las carpetas montadas desde gameinfo.txt y comenta expresamente que Half-Life: Source Deathmatch puede tomar materiales de la carpeta hl1 vecina.

**Límite de esta conclusión:** se verificó el código del parser, pero en esta ejecución no se convirtió un BSP real de la instalación Steam del usuario. El inspector añadido aquí valida cabecera y rangos; no valida geometría, materiales ni entidades. Hay que probar al menos un mapa real de hl1/maps antes de declarar compatibilidad completa.

## Formatos de mapas que reconoce el conversor de referencia

| Entrada | Soporte observado | Qué produce |
|---|---|---|
| Source 1 VBSP v19-v21 | Parser de 64 lumps; geometría, nodos/hojas, visibilidad, iluminación, entidades, brushes, displacements, game lumps y pakfile | PMAP + pack de props por mapa + navegación cuando hay info_node |
| GoldSrc BSP v30 | Parser separado; reconstrucción de brushes desde el árbol BSP y texturas desde WAD | PMAP + pack de props/navegación según contenido |
| BSP Source v17/v18, Source 2 o formatos desconocidos | Fuera del rango comprobado; debe rechazarse o añadirse un parser específico | No convertir |

El parser Source contempla lumps de entidades, planos, vértices, aristas, surfedges, caras, texinfo/texdata, modelos, nodos, hojas, brushes, brushsides, displacements, iluminación LDR/HDR, visibilidad, game lumps y pakfile. También reconoce lumps comprimidos con marcador LZMA. No significa que cada entidad o shader de todos los juegos Source se reproduzca fielmente.

## Modelos, materiales y texturas

### Modelos Source

tools/bspconv/models.py lee modelos Source Studio con firma IDST y requiere el conjunto de archivos:
- .mdl
- .vvd (firma interna IDSV)
- .dx90.vtx, .dx80.vtx, .sw.vtx o .vtx

El .phy se usa cuando existe para masa, superficie y colisión. El conversor elige un LOD que quepa en un presupuesto de triángulos y puede simplificar la malla. La ruta normal no conserva todos los bodygroups/skins como variantes completas; para NPCs hay una ruta separada que prepara animaciones. Esto no es un lector genérico de modelos GoldSrc.

### Materiales

Los mapas Source resuelven VMT y su $basetexture hacia VTF. El lector VTF maneja formatos comprimidos DXT y formatos de píxel comunes; los formatos no contemplados producen advertencias o quedan como textura ausente/color plano. Para GoldSrc, el conversor usa texturas WAD.

## Bloqueo importante: PMAP v6 frente a PMAP v5

El conversor actual de retcons-mod escribe **PMAP v6**:
- usa secciones PVSZ y SPVZ para visibilidad codificada;
- incorpora el nuevo tratamiento de bevels de colisión;
- guarda datos de textura en TXDT con offsets referidos al archivo.

El runtime de retcon26/PS2-GMOD inspeccionado declara **PMAP_VERSION 5** y busca las secciones antiguas PVS y SPVS. Su map_load() rechaza cualquier versión distinta de la compilada y muestra “not a v5 pmap”.

Por eso, **no se puede ejecutar directamente el PMAP generado por el conversor actual en el runtime PS2-GMOD de ese commit**. Cambiar solo el número de versión en el encabezado tampoco alcanza: faltan PVS/SPVS y hay diferencias en la representación de bevels.

Soluciones válidas:
1. Crear un exportador PS2 que escriba explícitamente el layout v5 y convierta PVSZ/SPVZ a PVS/SPVS, además de serializar bevels de forma compatible; o
2. Actualizar el runtime PS2 para PMAP v6, implementando y probando la decodificación de visibilidad y los bevels.

Para HLPS2-Engine conviene definir un formato de runtime PS2 documentado y versionado, sin asumir compatibilidad binaria con PSP ni con el viejo port.

## Adaptaciones necesarias para PS2

1. **BSP:** validar límites, counts, offsets y compresión antes de reservar memoria. Mantener parsers separados para Source y GoldSrc.
2. **Geometría:** convertir a vértices compactos, índices de 16 bits y lotes por material/celda; controlar tamaño de mapa y cantidad de triángulos.
3. **Visibilidad:** conservar PVS, pero medir el costo de memoria. La compresión de PMAP v6 exige un decoder compatible en runtime.
4. **Colisión:** limitar brushes/planes y convertir bevels/displacements a una representación que el trazador PS2 pueda consultar sin desbordar RAM.
5. **Modelos:** usar LOD y decimación para props; para NPCs, hornear animaciones o reducir huesos. El runtime no debe intentar cargar directamente MDL/VVD/VTX.
6. **Texturas:** reducir resolución y convertir VTF a un formato de GS (por ejemplo T8 con CLUT o RGBA5551); decidir mipmaps, swizzle y uso de VRAM.
7. **Memoria:** la PS2 tiene 32 MB. PS2-GMOD mide el bloque libre más grande y elige recursos low/high; su comentario estima unos 24 MB libres tras programa y buffers. HLPS2 debe medir su propio heap y no asumir ese mismo margen.
8. **Renderer:** PS2-GMOD manda a VU1 geometría de mapas y modelos iluminados en lotes, dejando clipping difícil en CPU. HLPS2 ya tiene cubo EE y prueba VU1→GS, pero aún debe demostrar transformación real de vértices en VU1 antes de integrar mapas.
9. **Audio:** PS2-GMOD usa audsrv/IOP, mezclador en hilo, 16 voces y salida estéreo 22050 Hz; el pack low de 16 kHz ahorra memoria frente al de 44.1 kHz. Es una referencia, no una integración hecha aquí.
10. **Input:** PS2-GMOD usa libpad en modo DualShock 2 analógico, con ambos sticks y mapeo a acciones del juego.
11. **Filesystem:** su P2PK empaqueta rutas largas en DATA.PAK; divide DATA.PAK/DATA1.PAK en partes menores de 2 GB por los seeks de 32 bits. Es preferible a depender de nombres 8.3 de ISO9660.
12. **Build:** la referencia PS2 integra PS2SDK, gsKit, dvp-as y módulos IOP (audsrv, DEV9, netman, smap). HLPS2 mantiene su build PS2SDK separado y no debe introducir dependencias hasta probarlas.

## Herramienta nueva en HLPS2-Engine

tools/asset_pipeline/inspect_bsp.py inspecciona solo la cabecera:
- identifica Source VBSP v19-v21 y GoldSrc v30;
- valida tamaño de cabecera y rangos de los lumps;
- cuenta lumps Source con marcador LZMA;
- ofrece JSON y self-test sintético.

No descomprime lumps ni convierte mapas. No puede determinar si un VBSP procede de Half-Life: Source: eso se confirma por la instalación/ruta y sus gameinfo.txt, no por la firma sola.

## Siguiente paso técnico

Obtener un BSP real de Half-Life: Source desde una instalación legítima, ejecutar inspect_bsp.py y después preparar un test de conversión host-side que genere un reporte de geometría/materiales sin escribir todavía un PMAP para PS2. Con ese resultado, diseñar el exportador PS2 versionado y agregar pruebas de ida y vuelta para su encabezado/secciones.
