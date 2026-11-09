EE_BIN = hlps2.elf
DVP_AS ?= dvp-as
EE_OBJS = src/main.o src/vu1_probe.o
EE_CFLAGS += -O2 -G0 -Wall -Wextra -Iinclude
EE_LIBS += -ldebug -ldraw -lgraph -ldma -lpacket -lm

src/vu1_probe.o: src/vu1_probe.vsm
	$(DVP_AS) $< -o $@

.PHONY: all clean
all: $(EE_BIN)

clean:
	$(RM) $(EE_BIN) $(EE_OBJS)

# Define EE_CC, EE_LD and the rest of the PS2 toolchain commands.
include $(PS2SDK)/Defs.make
include $(PS2SDK)/samples/Makefile.eeglobal
