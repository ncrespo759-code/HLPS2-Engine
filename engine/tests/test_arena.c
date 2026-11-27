#include "../core/arena.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main(void)
{
    uint8_t memory[128];
    hl_arena arena;
    void *a, *b;
    hl_arena_init(&arena, memory, sizeof(memory));
    a = hl_arena_alloc(&arena, 12u, 4u);
    b = hl_arena_alloc(&arena, 16u, 16u);
    assert(a != 0);
    assert(b != 0);
    assert(((uintptr_t)b & 15u) == 0u);
    assert(arena.allocations == 2u);
    assert(hl_arena_remaining(&arena) < sizeof(memory));
    assert(hl_arena_alloc(&arena, 4096u, 16u) == 0);
    assert(hl_arena_alloc(&arena, 1u, 3u) == 0);
    hl_arena_reset(&arena);
    assert(arena.used == 0u);
    assert(hl_arena_remaining(&arena) == sizeof(memory));
    puts("HLPS2 arena tests: OK");
    return 0;
}
