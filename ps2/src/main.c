#include <kernel.h>
#include <debug.h>
#include <tamtypes.h>
#include <math.h>

#include <dma.h>
#include <gif_tags.h>
#include <graph.h>
#include <gs_gp.h>
#include <gs_psm.h>
#include <packet.h>
#include <draw.h>

extern u32 hlps2_vu1_probe_size(void);

#define SCREEN_W 640
#define SCREEN_H 448
#define PACKET_QWORDS 128
#define CUBE_TRIANGLES 12

typedef struct {
    float x, y, z;
} vec3_t;

typedef struct {
    int a, b, c;
    unsigned char r, g, bcol;
    float depth;
} face_t;

static const vec3_t cube_vertices[8] = {
    {-1.0f, -1.0f, -1.0f}, { 1.0f, -1.0f, -1.0f},
    { 1.0f,  1.0f, -1.0f}, {-1.0f,  1.0f, -1.0f},
    {-1.0f, -1.0f,  1.0f}, { 1.0f, -1.0f,  1.0f},
    { 1.0f,  1.0f,  1.0f}, {-1.0f,  1.0f,  1.0f}
};

static const int cube_indices[CUBE_TRIANGLES][3] = {
    {0, 2, 1}, {0, 3, 2},
    {4, 5, 6}, {4, 6, 7},
    {0, 1, 5}, {0, 5, 4},
    {3, 7, 6}, {3, 6, 2},
    {1, 2, 6}, {1, 6, 5},
    {0, 4, 7}, {0, 7, 3}
};

static const unsigned char face_colors[6][3] = {
    {230, 70, 70}, {70, 210, 100}, {70, 130, 245},
    {245, 205, 65}, {190, 90, 230}, {55, 210, 220}
};

static int init_graphics(framebuffer_t *frame, zbuffer_t *zbuffer)
{
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

    return graph_initialize(frame->address, frame->width, frame->height,
                            frame->psm, 0, 0);
}

static void setup_drawing_environment(packet_t *packet,
                                      framebuffer_t *frame,
                                      zbuffer_t *zbuffer)
{
    qword_t *q = packet->data;
    q = draw_setup_environment(q, 0, frame, zbuffer);
    q = draw_finish(q);
    dma_channel_send_normal(DMA_CHANNEL_GIF, packet->data,
                            (int)(q - packet->data), 0, 0);
    draw_wait_finish();
}

static void transform_vertex(const vec3_t *in, vec3_t *out,
                             float sx, float cx, float sy, float cy)
{
    float x = in->x * cy + in->z * sy;
    float z = -in->x * sy + in->z * cy;
    out->x = x;
    out->y = in->y * cx - z * sx;
    out->z = in->y * sx + z * cx + 4.2f;
}

static int project_vertex(const vec3_t *v, int *x, int *y)
{
    float inv_z;
    if (v->z < 0.5f)
        return -1;

    inv_z = 220.0f / v->z;
    *x = (int)(320.0f + v->x * inv_z);
    *y = (int)(224.0f - v->y * inv_z);
    return 0;
}

static float triangle_depth(const vec3_t *a, const vec3_t *b,
                            const vec3_t *c)
{
    return (a->z + b->z + c->z) * (1.0f / 3.0f);
}

static void sort_faces_far_to_near(face_t *faces, int count)
{
    int i, j;
    for (i = 1; i < count; ++i) {
        face_t key = faces[i];
        j = i - 1;
        while (j >= 0 && faces[j].depth < key.depth) {
            faces[j + 1] = faces[j];
            --j;
        }
        faces[j + 1] = key;
    }
}

static void emit_triangle(qword_t **cursor, const face_t *face,
                          const int sx[8], const int sy[8])
{
    qword_t *q = *cursor;

    PACK_GIFTAG(q, GIF_SET_TAG(5, 1, 0, 0, 0, 1), GIF_REG_AD);
    ++q;
    PACK_GIFTAG(q, GIF_SET_PRIM(3, 0, 0, 0, 0, 0, 0, 0, 0), GIF_REG_PRIM);
    ++q;
    PACK_GIFTAG(q, GIF_SET_RGBAQ(face->r, face->g, face->bcol,
                                 0x80, 0x3F800000), GIF_REG_RGBAQ);
    ++q;

    PACK_GIFTAG(q, GIF_SET_XYZ((sx[face->a] << 4) + (2048 << 4),
                               (sy[face->a] << 4) + (2048 << 4), 0),
                GIF_REG_XYZ2);
    ++q;
    PACK_GIFTAG(q, GIF_SET_XYZ((sx[face->b] << 4) + (2048 << 4),
                               (sy[face->b] << 4) + (2048 << 4), 0),
                GIF_REG_XYZ2);
    ++q;
    PACK_GIFTAG(q, GIF_SET_XYZ((sx[face->c] << 4) + (2048 << 4),
                               (sy[face->c] << 4) + (2048 << 4), 0),
                GIF_REG_XYZ2);
    ++q;

    *cursor = q;
}

static void draw_cube(packet_t *packet, framebuffer_t *frame, float angle)
{
    vec3_t transformed[8];
    face_t visible[CUBE_TRIANGLES];
    int sx[8], sy[8];
    int i, count = 0;
    float cx = cosf(angle * 0.73f);
    float sxr = sinf(angle * 0.73f);
    float cy = cosf(angle);
    float syr = sinf(angle);
    qword_t *q;

    for (i = 0; i < 8; ++i) {
        transform_vertex(&cube_vertices[i], &transformed[i],
                         sxr, cx, syr, cy);
        if (project_vertex(&transformed[i], &sx[i], &sy[i]) < 0)
            return;
    }

    for (i = 0; i < CUBE_TRIANGLES; ++i) {
        const vec3_t *a = &transformed[cube_indices[i][0]];
        const vec3_t *b = &transformed[cube_indices[i][1]];
        const vec3_t *c = &transformed[cube_indices[i][2]];
        vec3_t ab, ac;
        float nx, ny, nz;
        int color = i / 2;

        ab.x = b->x - a->x; ab.y = b->y - a->y; ab.z = b->z - a->z;
        ac.x = c->x - a->x; ac.y = c->y - a->y; ac.z = c->z - a->z;
        nx = ab.y * ac.z - ab.z * ac.y;
        ny = ab.z * ac.x - ab.x * ac.z;
        nz = ab.x * ac.y - ab.y * ac.x;

        /* Back-face culling against the camera at the origin. */
        if (nx * (-a->x) + ny * (-a->y) + nz * (-a->z) <= 0.0f)
            continue;

        visible[count].a = cube_indices[i][0];
        visible[count].b = cube_indices[i][1];
        visible[count].c = cube_indices[i][2];
        visible[count].r = face_colors[color][0];
        visible[count].g = face_colors[color][1];
        visible[count].bcol = face_colors[color][2];
        visible[count].depth = triangle_depth(a, b, c);
        ++count;
    }

    sort_faces_far_to_near(visible, count);

    dma_wait_fast();
    q = packet->data;
    q = draw_clear(q, 0, 0, 0, frame->width, frame->height, 8, 16, 40);
    for (i = 0; i < count; ++i)
        emit_triangle(&q, &visible[i], sx, sy);
    q = draw_finish(q);

    dma_channel_send_normal(DMA_CHANNEL_GIF, packet->data,
                            (int)(q - packet->data), 0, 0);
    draw_wait_finish();
}

int main(void)
{
    framebuffer_t frame;
    zbuffer_t zbuffer;
    packet_t *packet;
    float angle = 0.0f;

    init_scr();
    scr_printf("HLPS2-Engine: native EE 3D cube test\\n");
    scr_printf("VU1 microcode linked: %u bytes (not executed yet)\\n",\n               hlps2_vu1_probe_size());

    dma_channel_initialize(DMA_CHANNEL_GIF, 0, 0);
    dma_channel_fast_waits(DMA_CHANNEL_GIF);

    if (init_graphics(&frame, &zbuffer) < 0) {
        scr_printf("ERROR: GS framebuffer initialization failed\n");
        for (;;) SleepThread();
    }

    packet = packet_init(PACKET_QWORDS, PACKET_NORMAL);
    if (packet == 0) {
        scr_printf("ERROR: GIF packet allocation failed\n");
        for (;;) SleepThread();
    }

    setup_drawing_environment(packet, &frame, &zbuffer);

    for (;;) {
        draw_cube(packet, &frame, angle);
        angle += 0.025f;
        if (angle > 6.2831853f)
            angle -= 6.2831853f;
        graph_wait_vsync();
    }

    return 0;
}
