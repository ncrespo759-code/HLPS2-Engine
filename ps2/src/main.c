#include <kernel.h>
#include <debug.h>
#include <tamtypes.h>

#include <dma.h>
#include <gif_tags.h>
#include <graph.h>
#include <gs_gp.h>
#include <gs_psm.h>
#include <packet.h>
#include <draw.h>

/*
 * GS bring-up test.
 *
 * This is the first native graphics path for HLPS2-Engine:
 * EE prepares a small GIF packet, DMA sends it to the GS, and the GS
 * draws a colored triangle. No gsKit dependency and no VU1 code yet.
 */
static int init_graphics(framebuffer_t *frame, zbuffer_t *zbuffer)
{
    frame->width = 640;
    frame->height = 448;
    frame->psm = GS_PSM_32;
    frame->mask = 0;
    frame->address = graph_vram_allocate(
        frame->width, frame->height, frame->psm, GRAPH_ALIGN_PAGE);

    if ((int)frame->address < 0) {
        return -1;
    }

    zbuffer->enable = 0;
    zbuffer->method = 0;
    zbuffer->address = 0;
    zbuffer->zsm = 0;
    zbuffer->mask = 0;

    return graph_initialize(
        frame->address, frame->width, frame->height, frame->psm, 0, 0);
}

static void setup_drawing_environment(packet_t *packet,
                                      framebuffer_t *frame,
                                      zbuffer_t *zbuffer)
{
    qword_t *q = packet->data;

    q = draw_setup_environment(q, 0, frame, zbuffer);
    q = draw_finish(q);

    dma_channel_send_normal(
        DMA_CHANNEL_GIF, packet->data, (int)(q - packet->data), 0, 0);
    draw_wait_finish();
}

static void draw_test_triangle(packet_t *packet,
                               framebuffer_t *frame)
{
    qword_t *q;

    dma_wait_fast();
    q = packet->data;

    /* Clear the framebuffer to a dark blue background. */
    q = draw_clear(q, 0, 0, 0, frame->width, frame->height, 8, 16, 40);

    /*
     * GIF packed A+D register list:
     * PRIM, RGBAQ, and three XYZ2 vertices form one flat-shaded triangle.
     * GS screen coordinates use the standard 2048,2048 origin.
     */
    PACK_GIFTAG(q, GIF_SET_TAG(5, 1, 0, 0, 0, 1), GIF_REG_AD);
    q++;

    PACK_GIFTAG(q, GIF_SET_PRIM(3, 0, 0, 0, 0, 0, 0, 0, 0), GIF_REG_PRIM);
    q++;

    PACK_GIFTAG(q, GIF_SET_RGBAQ(40, 210, 255, 0x80, 0x3F800000), GIF_REG_RGBAQ);
    q++;

    PACK_GIFTAG(q, GIF_SET_XYZ((160 << 4) + (2048 << 4),
                               (340 << 4) + (2048 << 4), 0), GIF_REG_XYZ2);
    q++;
    PACK_GIFTAG(q, GIF_SET_XYZ((320 << 4) + (2048 << 4),
                               (90 << 4) + (2048 << 4), 0), GIF_REG_XYZ2);
    q++;
    PACK_GIFTAG(q, GIF_SET_XYZ((480 << 4) + (2048 << 4),
                               (340 << 4) + (2048 << 4), 0), GIF_REG_XYZ2);
    q++;

    q = draw_finish(q);

    dma_channel_send_normal(
        DMA_CHANNEL_GIF, packet->data, (int)(q - packet->data), 0, 0);
    draw_wait_finish();
}

int main(void)
{
    framebuffer_t frame;
    zbuffer_t zbuffer;
    packet_t *packet;

    init_scr();
    scr_printf("HLPS2-Engine: initializing native GS test\n");

    dma_channel_initialize(DMA_CHANNEL_GIF, 0, 0);
    dma_channel_fast_waits(DMA_CHANNEL_GIF);

    if (init_graphics(&frame, &zbuffer) < 0) {
        scr_printf("ERROR: GS framebuffer initialization failed\n");
        for (;;) {
            SleepThread();
        }
    }

    packet = packet_init(32, PACKET_NORMAL);
    if (packet == 0) {
        scr_printf("ERROR: could not allocate GIF packet\n");
        for (;;) {
            SleepThread();
        }
    }

    setup_drawing_environment(packet, &frame, &zbuffer);

    for (;;) {
        draw_test_triangle(packet, &frame);
        graph_wait_vsync();
    }

    return 0;
}
