#include <tamtypes.h>

/* Symbols emitted by dvp-as into the .vudata section. */
extern u32 hlps2_vu1_probe_CodeStart[] __attribute__((section(".vudata")));
extern u32 hlps2_vu1_probe_CodeEnd[] __attribute__((section(".vudata")));

u32 hlps2_vu1_probe_size(void)
{
    return (u32)hlps2_vu1_probe_CodeEnd - (u32)hlps2_vu1_probe_CodeStart;
}
