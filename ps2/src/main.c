#include <kernel.h>
#include <debug.h>
#include <stdio.h>

/*
 * Visible PS2 boot diagnostic.
 * This is a platform bring-up test, not an HL2 engine implementation.
 */
int main(void)
{
    init_scr();

    scr_printf("\\n");
    scr_printf("HLPS2-Engine - PS2 BOOT TEST\\n");
    scr_printf("-----------------------------\\n");
    scr_printf("Emotion Engine: running\\n");
    scr_printf("PS2SDK: initialized\\n");
    scr_printf("Graphics test: debug screen active\\n");
    scr_printf("\\n");
    scr_printf("HL2 renderer and asset loader: NOT IMPLEMENTED\\n");

    for (;;) {
        SleepThread();
    }

    return 0;
}
