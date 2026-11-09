#include <kernel.h>
#include <debug.h>
#include <tamtypes.h>
#include <dma.h>
#include <graph.h>
#include <draw.h>
#include <gs_psm.h>
#include <packet2.h>

#define SCREEN_W 640
#define SCREEN_H 448

extern int hlps2_vu1_draw_test_triangle(void);

static int init_test_screen(framebuffer_t *frame, zbuffer_t *zbuffer)
{
    packet2_t *packet;

    frame->width = SCREEN_W;
    frame->height = SCREEN_H;
    frame->psm = GS_PSM_32;
    frame->mask = 0;
    frame->address = graph_vram_allocate(
        frame->width, frame->height, frame->psm, GRAPH_ALIGN_PAGE);
    if ((int)frame->address < 0)
        return -1;

    zbuffer->enable = 0;
    zbuffer->method = 0;
    zbuffer->address = 0;
    zbuffer->zsm = 0;
    zbuffer->mask = 0;

    if (graph_initialize(frame->address, frame->width, frame->height,
                         frame->psm, 0, 0) < 0)
        return -2;

    packet = packet2_create(32, P2_TYPE_NORMAL, P2_MODE_NORMAL, 0);
    if (packet == 0)
        return -3;

    packet2_update(packet, draw_setup_environment(
        packet->next, 0, frame, zbuffer));
    packet2_update(packet, draw_finish(packet->next));
    dma_channel_send_packet2(packet, DMA_CHANNEL_GIF, 1);
    dma_wait_fast();
    packet2_free(packet);
    return 0;
}

static void clear_test_screen(framebuffer_t *frame, zbuffer_t *zbuffer)
{
    packet2_t *packet = packet2_create(32, P2_TYPE_NORMAL, P2_MODE_NORMAL, 0);
    if (packet == 0)
        return;

    packet2_update(packet, draw_clear(packet->next, 0, 0, 0,
        frame->width, frame->height, 8, 16, 40));
    packet2_update(packet, draw_finish(packet->next));
    dma_channel_send_packet2(packet, DMA_CHANNEL_GIF, 1);
    draw_wait_finish();
    packet2_free(packet);
    (void)zbuffer;
}

int main(void)
{
    framebuffer_t frame;
    zbuffer_t zbuffer;
    int result;

    init_scr();
    scr_printf("HLPS2 VU1 -> GS triangle test\n");
    scr_printf("Initializing GIF and VIF1...\n");

    dma_channel_initialize(DMA_CHANNEL_GIF, 0, 0);
    dma_channel_fast_waits(DMA_CHANNEL_GIF);

    result = init_test_screen(&frame, &zbuffer);
    if (result < 0) {
        scr_printf("GS initialization failed: %d\n", result);
        for (;;) SleepThread();
    }

    clear_test_screen(&frame, &zbuffer);
    scr_printf("Sending triangle through VU1 XGKICK...\n");
    result = hlps2_vu1_draw_test_triangle();
    if (result < 0)
        scr_printf("VU1 triangle setup failed: %d\n", result);
    else
        scr_printf("VU1 XGKICK submitted. Triangle should be visible.\n");

    draw_wait_finish();
    for (;;)
        graph_wait_vsync();

    return 0;
}
