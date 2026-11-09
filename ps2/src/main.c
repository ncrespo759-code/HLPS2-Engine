#include <kernel.h>
#include <stdio.h>

/*
 * Minimal boot smoke test.
 * This is deliberately not presented as an HL2 engine implementation.
 * printf output is intended for a configured PS2SDK debug/TTY environment.
 */
int main(void)
{
    printf("HLPS2-Engine: PS2 platform bootstrap\n");
    printf("Target: Emotion Engine / PS2SDK\n");
    printf("Engine systems are not implemented yet.\n");

    for (;;) {
        SleepThread();
    }

    return 0;
}
