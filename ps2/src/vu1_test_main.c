#include <kernel.h>
#include <debug.h>
#include <tamtypes.h>

extern u32 hlps2_vu1_probe_size(void);
extern int hlps2_vu1_run_isolated_probe(void);

int main(void)
{
    int result;

    init_scr();
    scr_printf("HLPS2 VU1 isolated execution test\n");
    scr_printf("Microprogram linked: %u bytes\n", hlps2_vu1_probe_size());
    scr_printf("Initializing VIF1...\n");

    result = hlps2_vu1_run_isolated_probe();
    if (result == 0)
        scr_printf("VU1 probe completed (MSCAL + FLUSHE).\n");
    else
        scr_printf("VU1 probe setup failed: %d\n", result);

    scr_printf("Test finished. Safe to reset the emulator.\n");
    for (;;)
        SleepThread();

    return 0;
}
