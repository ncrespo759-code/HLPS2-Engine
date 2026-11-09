/*
 * Isolated VU1 execution test.
 *
 * Uses the PS2SDK packet2 sequence from ee/draw/samples/vu1:
 * upload with TTE enabled, wait for VIF1 DMA, then start with MSCAL
 * and wait for FLUSHE. This test does not touch the stable cube ELF.
 */
#include <tamtypes.h>
#include <dma.h>
#include <packet2.h>
#include <packet2_chain.h>
#include <packet2_vif.h>
#include <packet2_utils.h>

extern u32 hlps2_vu1_probe_CodeStart[];
extern u32 hlps2_vu1_probe_CodeEnd[];

static int upload_probe(void)
{
    packet2_t *packet;

    packet = packet2_create(8, P2_TYPE_NORMAL, P2_MODE_CHAIN, 1);
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

    packet = packet2_create(8, P2_TYPE_NORMAL, P2_MODE_CHAIN, 1);
    if (packet == 0)
        return -1;

    packet2_utils_vu_add_start_program(packet, 0);
    packet2_chain_open_cnt(packet, 0, 0, 0);
    packet2_vif_flushe(packet, 0);
    packet2_chain_close_tag(packet);
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
