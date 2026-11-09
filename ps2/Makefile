EE_BIN = hlps2.elf
DVP_AS ?= dvp-as
EE_OBJS = src/main.o src/vu1_probe.o src/vu1_probe_c.o
EE_CFLAGS += -O2 -G0 -Wall -Wextra -Iinclude
EE_LIBS += -ldebug -ldraw -lgraph -ldma -lpacket -lm

src/vu1_probe.o: src/vu1_probe.vsm
	$(DVP_AS) $< -o $@

src/vu1_triangle.o: src/vu1_triangle.vsm
	$(DVP_AS) $< -o $@

src/vu1_probe_c.o: src/vu1_probe.c
	$(EE_CC) $(EE_CFLAGS) -c $< -o $@

.PHONY: all clean vu1-test vu1-triangle-test
all: $(EE_BIN)

# Build a separate test ELF. The stable cube target never links or calls
# the experimental VIF1/VU1 runtime.
vu1-test:
	$(MAKE) EE_BIN=hlps2-vu1-test.elf EE_OBJS="src/vu1_test_main.o src/vu1_runtime.o src/vu1_probe.o src/vu1_probe_c.o" EE_LIBS="$(EE_LIBS) -lpacket2" all

# Separate VU1 -> GS XGKICK triangle test; the stable cube ELF is untouched.
vu1-triangle-test:
	$(MAKE) EE_BIN=hlps2-vu1-triangle-test.elf EE_OBJS="src/vu1_triangle_main.o src/vu1_triangle_runtime.o src/vu1_triangle.o" EE_LIBS="$(EE_LIBS) -lpacket2" all

clean:
	$(RM) $(EE_BIN) hlps2-vu1-test.elf $(EE_OBJS) src/vu1_test_main.o src/vu1_runtime.o src/vu1_triangle_main.o src/vu1_triangle_runtime.o src/vu1_triangle.o

# Define EE_CC, EE_LD and the rest of the PS2 toolchain commands.
include $(PS2SDK)/Defs.make
include $(PS2SDK)/samples/Makefile.eeglobal
