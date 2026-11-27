EE_BIN = hlps2-bootstrap.elf
EE_OBJS = main.o
EE_CFLAGS += -O2 -G0 -Wall -Wextra
EE_LIBS += -ldebug -ldraw -lgraph -ldma -lpacket

.PHONY: all clean
all: $(EE_BIN)

clean:
	$(RM) $(EE_BIN) $(EE_OBJS)

include $(PS2SDK)/Defs.make
include $(PS2SDK)/samples/Makefile.eeglobal
