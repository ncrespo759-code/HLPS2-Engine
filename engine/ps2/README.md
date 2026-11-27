# HLPS2 PS2 bootstrap

Este directorio contiene el primer ejecutable nativo de la línea nueva. No enlaza ni incluye los prototipos antiguos ubicados en `ps2/`.

## Meta de esta fase

- Arrancar en EE/R5900 con PS2SDK.
- Inicializar un framebuffer GS de 640x448 en 32 bits.
- Enviar un paquete GIF para limpiar la pantalla a un color azul de prueba.
- Mantener el cuadro estable esperando VSync.

Se usan las bibliotecas de bajo nivel `libgraph`, `libdraw`, `libdma` y `libpacket` del PS2SDK para la puesta en marcha del hardware. **No se usa GSKit**. Esta primera prueba valida arranque y presentación; todavía no es el renderer final VU1 ni un motor jugable.

## Compilar

Desde la raíz del repositorio, con PS2SDK configurado:

```sh
make -C engine/ps2 clean all
```

El resultado es `engine/ps2/hlps2-bootstrap.elf`.
