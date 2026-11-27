#include "arena.h"

#include <stdint.h>

static int is_power_of_two(size_t value)
{
    return value != 0u && (value & (value - 1u)) == 0u;
}

void hl_arena_init(hl_arena *arena, void *memory, size_t capacity)
{
    if (!arena) return;
    arena->base = (uint8_t *)memory;
    arena->capacity = memory ? capacity : 0u;
    arena->used = 0u;
    arena->allocations = 0u;
}

void *hl_arena_alloc(hl_arena *arena, size_t size, size_t alignment)
{
    size_t mask, aligned, padding;
    if (!arena || !arena->base || size == 0u) return 0;
    if (!is_power_of_two(alignment)) return 0;
    mask = alignment - 1u;
    if (arena->used > SIZE_MAX - mask) return 0;
    aligned = (arena->used + mask) & ~mask;
    if (aligned < arena->used) return 0;
    padding = aligned - arena->used;
    if (padding > arena->capacity - arena->used) return 0;
    if (size > arena->capacity - arena->used - padding) return 0;
    arena->used = aligned + size;
    arena->allocations++;
    return arena->base + aligned;
}

void hl_arena_reset(hl_arena *arena)
{
    if (!arena) return;
    arena->used = 0u;
    arena->allocations = 0u;
}

size_t hl_arena_remaining(const hl_arena *arena)
{
    if (!arena || arena->used > arena->capacity) return 0u;
    return arena->capacity - arena->used;
}
