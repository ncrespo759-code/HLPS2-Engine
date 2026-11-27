#include <kernel.h>
#include <debug.h>
#include <tamtypes.h>

#include <dma.h>
#include <graph.h>
#include <gs_psm.h>
#include <packet.h>
#include <draw.h>

#define SCREEN_W 640
#define SCREEN_H 448
#define PACKET_QWORDS 32

int main(void)
{
    framebuffer_t frame;
    zbuffer_t zbuffer;
    packet_t *packet;
    qword_t *q;

    init_scr();
    scr_printf("HLPS2 native bootstrap\n");
    scr_printf("Half-Life 1 engine - clean EE target\n");

    dma_channel_initialize(DMA_CHANNEL_GIF, 0, 0);
    dma_channel_fast_waits(DMA_CHANNEL_GIF);

    frame.width = SCREEN_W;
    frame.height = SCREEN_H;
    frame.psm = GS_PSM_32;
    frame.mask = 0;
    frame.address = graph_vram_allocate(
        frame.width, frame.height, frame.psm, GRAPH_ALIGN_PAGE);
    if ((int)frame.address < 0) {
        scr_printf("ERROR: framebuffer VRAM allocation\n");
        for (;;) SleepThread();
    }

    zbuffer.enable = 0;
    zbuffer.method = 0;
    zbuffer.address = 0;
    zbuffer.zsm = 0;
    zbuffer.mask = 0;

    if (graph_initialize(frame.address, frame.width, frame.height,
                         frame.psm, 0, 0) < 0) {
        scr_printf("ERROR: GS initialization\n");
        for (;;) SleepThread();
    }

    packet = packet_init(PACKET_QWORDS, PACKET_NORMAL);
    if (packet == 0) {
        scr_printf("ERROR: GIF packet allocation\n");
        for (;;) SleepThread();
    }

    q = packet->data;
    q = draw_setup_environment(q, 0, &frame, &zbuffer);
    q = draw_clear(q, 0, 0, 0, SCREEN_W, SCREEN_H, 24, 40, 72);
    q = draw_finish(q);
    dma_channel_send_normal(DMA_CHANNEL_GIF, packet->data,
                            (int)(q - packet->data), 0, 0);
    draw_wait_finish();

    scr_printf("GS framebuffer ready. Blue test screen active.\n");
    for (;;) {
        graph_wait_vsync();
    }

    return 0;
}
