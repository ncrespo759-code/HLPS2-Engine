/* Minimal EE-side metadata for the VU1 probe.
 * Keep this file independent of PS2SDK headers: the probe only reports
 * the byte span of the assembled microprogram.
 */
typedef unsigned int hlps2_u32;

extern unsigned char hlps2_vu1_probe_CodeStart[];
extern unsigned char hlps2_vu1_probe_CodeEnd[];

hlps2_u32 hlps2_vu1_probe_size(void)
{
    return (hlps2_u32)(hlps2_vu1_probe_CodeEnd -
                       hlps2_vu1_probe_CodeStart);
}
