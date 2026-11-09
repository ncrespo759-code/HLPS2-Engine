/*
 * Isolated VU1 execution test.
 *
 * Follow the PS2SDK ee/draw/samples/vu1 packet sequence:
 * upload the microprogram, wait for VIF1 DMA, then submit a small
 * chain containing MSCAL and an END tag. No GIF/GS rendering here.
 */
#include <tamtypes.h>
#include <dma.h>
#include <packet2.h>
#include <packet2_vif.h>
#include <packet2_utils.h>

extern u32 hlps2_vu1_probe_CodeStart[];
extern u32 hlps2_vu1_probe_CodeEnd[];

static int upload_probe(void)
{
    u32 packet_size;
    packet2_t *packet;

    packet_size = packet2_utils_get_packet_size_for_program(
        hlps2_vu1_probe_CodeStart, hlps2_vu1_probe_CodeEnd) + 1;
    packet = packet2_create(packet_size, P2_TYPE_NORMAL, P2_MODE_CHAIN, 1);
    if (packet == 0)
        return -1;

    packet2_vif_add_micro_program(packet, 0,
                                  hlps2_vu1_probe_CodeStart,
                                  hlps2_vu1_probe_CodeEnd);
    packet2_utils_vu_add_end_tag(packet);
    dma_channel_send_packet2(packet, DMA_CHANNEL_VIF1, 1);
    dma_channel_wait(DMA_CHANNEL_VIF1, 0);
    packet2_free(packet);
    return 0;
}

static int execute_probe(void)
{
    packet2_t *packet;

    /* Same minimal launch sequence used by the PS2SDK VU1 sample. */
    packet = packet2_create(2, P2_TYPE_NORMAL, P2_MODE_CHAIN, 1);
    if (packet == 0)
        return -1;

    packet2_utils_vu_add_start_program(packet, 0);
    packet2_utils_vu_add_end_tag(packet);
    dma_channel_send_packet2(packet, DMA_CHANNEL_VIF1, 1);
    dma_channel_wait(DMA_CHANNEL_VIF1, 0);
    packet2_free(packet);
    return 0;
}

int hlps2_vu1_run_isolated_probe(void)
{
    dma_channel_initialize(DMA_CHANNEL_VIF1, 0, 0);
    dma_channel_fast_waits(DMA_CHANNEL_VIF1);

    if (upload_probe() < 0)
        return -1;
    if (execute_probe() < 0)
        return -2;
    return 0;
}
