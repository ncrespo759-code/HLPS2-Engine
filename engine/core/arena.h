#ifndef HLPS2_ARENA_H
#define HLPS2_ARENA_H

#include <stddef.h>
#include <stdint.h>

typedef struct hl_arena {
    uint8_t *base;
    size_t capacity;
    size_t used;
    uint32_t allocations;
} hl_arena;

void hl_arena_init(hl_arena *arena, void *memory, size_t capacity);
void *hl_arena_alloc(hl_arena *arena, size_t size, size_t alignment);
void hl_arena_reset(hl_arena *arena);
size_t hl_arena_remaining(const hl_arena *arena);

#endif
