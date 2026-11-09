/*
 * One-shot VU1 execution probe.
 *
 * Uploads the tiny linked microprogram through VIF1, starts it at micro
 * address zero, and waits for FLUSHE. It deliberately emits no GIF data;
 * the existing EE/GS cube remains the visible rendering reference.
 */
#include <tamtypes.h>
#include <dma.h>
#include <packet2.h>
#include <packet2_chain.h>
#include <packet2_vif.h>
#include <packet2_utils.h>

extern u32 hlps2_vu1_probe_CodeStart[];
extern u32 hlps2_vu1_probe_CodeEnd[];

int hlps2_vu1_execute_probe(void)
{
    packet2_t *packet;
    int result;

    packet = packet2_create(16, P2_TYPE_NORMAL, P2_MODE_CHAIN, 0);
    if (packet == 0)
        return -1;

    /*
     * packet2_vif_add_micro_program emits the REF + MPG sequence.
     * The helper then emits FLUSH + MSCAL. FLUSHE blocks VIF1 until
     * the VU1 program (which ends with the E bit) has completed.
     */
    packet2_vif_add_micro_program(packet, 0,
                                  hlps2_vu1_probe_CodeStart,
                                  hlps2_vu1_probe_CodeEnd);
    packet2_utils_vu_add_start_program(packet, 0);

    packet2_chain_open_cnt(packet, 0, 0, 0);
    packet2_vif_flushe(packet, 0);
    packet2_chain_close_tag(packet);
    packet2_utils_vu_add_end_tag(packet);

    if (dma_channel_initialize(DMA_CHANNEL_VIF1, 0, 0) < 0) {
        packet2_free(packet);
        return -2;
    }

    dma_channel_fast_waits(DMA_CHANNEL_VIF1);
    dma_channel_send_packet2(packet, DMA_CHANNEL_VIF1, 1);
    result = dma_channel_wait(DMA_CHANNEL_VIF1, 0);

    packet2_free(packet);
    return result;
}
