# HLPS2 Native Engine

Motor nuevo para **Half-Life 1 en PlayStation 2**, desarrollado desde cero.

Esta carpeta es la implementación nueva. No depende de Xash3D, del port de Nintendo 64 ni de los antiguos prototipos gráficos del repositorio.

## Reglas

- C y ensamblador MIPS/R5900 cuando sea necesario.
- Código común separado de los backends EE/VU/GS e IOP.
- Presupuesto de memoria explícito para los 32 MiB de RAM principal.
- Sin asignaciones ilimitadas ni cargas directas de assets de PC.
- No depender de Internet para jugar; red local solo si se implementa más adelante.
- Cada subsistema debe tener pruebas host-side y, cuando corresponda, una prueba en hardware PS2.

## Primer subsistema

core/arena.* implementa un asignador lineal acotado y sin dependencia de malloc. Será la base para los pools de entidades, geometría y recursos.
