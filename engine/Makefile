CC ?= cc
CFLAGS ?= -std=c99 -O2 -Wall -Wextra -Werror -pedantic

.PHONY: test clean

test: test_arena
	./test_arena

test_arena: core/arena.c tests/test_arena.c core/arena.h
	$(CC) $(CFLAGS) core/arena.c tests/test_arena.c -o $@

clean:
	rm -f test_arena
