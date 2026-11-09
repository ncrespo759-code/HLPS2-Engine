EE_BIN = hlps2.elf
EE_OBJS = src/main.o
EE_CFLAGS += -O2 -G0 -Wall -Wextra -Iinclude

.PHONY: all clean
all: $(EE_BIN)

clean:
	$(RM) $(EE_BIN) $(EE_OBJS)

include $(PS2SDK)/samples/Makefile.eeglobal
