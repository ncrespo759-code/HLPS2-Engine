/*
 * Isolated VU1 -> GS triangle bridge.
 *
 * The EE builds a small packed GIF packet and UNPACKs it into VU1 data
 * memory. VU1 then emits that packet to the GS using XGKICK. This isolates
 * the VU1/GIF path before adding vertex transforms in a later microprogram.
 */
#include <tamtypes.h>
#include <dma.h>
#include <gif_tags.h>
#include <gs_gp.h>
#include <packet2.h>
#include <packet2_vif.h>
#include <packet2_utils.h>

extern u32 hlps2_vu1_triangle_CodeStart[];
extern u32 hlps2_vu1_triangle_CodeEnd[];

/* Six qwords: one GIF tag followed by five packed A+D writes. */
static u64 triangle_gif[12] __attribute__((aligned(16)));

static void build_triangle_packet(void)
{
    const u64 origin = (u64)(2048 << 4);

    triangle_gif[0] = GIF_SET_TAG(5, 1, 0, 0, GIF_FLG_PACKED, 1);
    triangle_gif[1] = GIF_REG_AD;

    triangle_gif[2] = GIF_SET_PRIM(3, 0, 0, 0, 0, 0, 0, 0, 0);
    triangle_gif[3] = GIF_REG_PRIM;

    triangle_gif[4] = GIF_SET_RGBAQ(40, 220, 255, 0x80, 0x3F800000);
    triangle_gif[5] = GIF_REG_RGBAQ;

    triangle_gif[6] = GIF_SET_XYZ((180 << 4) + origin,
                                  (340 << 4) + origin, 0);
    triangle_gif[7] = GIF_REG_XYZ2;
    triangle_gif[8] = GIF_SET_XYZ((320 << 4) + origin,
                                  (120 << 4) + origin, 0);
    triangle_gif[9] = GIF_REG_XYZ2;
    triangle_gif[10] = GIF_SET_XYZ((460 << 4) + origin,
                                   (340 << 4) + origin, 0);
    triangle_gif[11] = GIF_REG_XYZ2;
}

static int upload_triangle_microprogram(void)
{
    u32 packet_size;
    packet2_t *packet;

    packet_size = packet2_utils_get_packet_size_for_program(
        hlps2_vu1_triangle_CodeStart, hlps2_vu1_triangle_CodeEnd) + 1;
    packet = packet2_create(packet_size, P2_TYPE_NORMAL, P2_MODE_CHAIN, 1);
    if (packet == 0)
        return -1;

    packet2_vif_add_micro_program(packet, 0,
                                  hlps2_vu1_triangle_CodeStart,
                                  hlps2_vu1_triangle_CodeEnd);
    packet2_utils_vu_add_end_tag(packet);
    dma_channel_send_packet2(packet, DMA_CHANNEL_VIF1, 1);
    dma_channel_wait(DMA_CHANNEL_VIF1, 0);
    packet2_free(packet);
    return 0;
}

int hlps2_vu1_draw_test_triangle(void)
{
    packet2_t *packet;

    dma_channel_initialize(DMA_CHANNEL_VIF1, 0, 0);
    dma_channel_fast_waits(DMA_CHANNEL_VIF1);

    if (upload_triangle_microprogram() < 0)
        return -1;

    build_triangle_packet();
    packet = packet2_create(16, P2_TYPE_NORMAL, P2_MODE_CHAIN, 1);
    if (packet == 0)
        return -2;

    /* Six qwords are copied into VU1 data memory starting at address 0. */
    packet2_utils_vu_add_unpack_data(packet, 0, triangle_gif, 6, 0);
    packet2_utils_vu_add_start_program(packet, 0);
    packet2_utils_vu_add_end_tag(packet);

    dma_channel_send_packet2(packet, DMA_CHANNEL_VIF1, 1);
    dma_channel_wait(DMA_CHANNEL_VIF1, 0);
    packet2_free(packet);
    return 0;
}
