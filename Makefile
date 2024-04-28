# ======================================================================
# Makefile for the upditerm demo program
# ======================================================================

AVR		= attiny412
F_CPU		= 3333333

PROGRAMMER	= serialupdi
PORT		= /dev/UPDI
BAUDRATE	= 115200
AVRDUDE		= avrdude -q -p $(AVR) -c $(PROGRAMMER) -P $(PORT) -b $(BAUDRATE)
FLASH_CMD	= $(AVRDUDE) -U flash:w:

MAIN		= demo
MODULES		= updi_uart.c updi_stdio.c
CFILES		= $(MAIN).c $(MODULES)
HFILES		= $(subst .c,.h,$(MODULES))
OBJECTS		= $(subst .c,.o,$(CFILES))

TOOLS		= /usr/local/avr-gcc-13.2.0-x64-linux/bin
CC		= $(TOOLS)/avr-gcc
CFLAGS		= -Wall -Os --param=min-pagesize=0 -DF_CPU=$(F_CPU)
CFLAGS		+= -ffunction-sections
LDFLAGS 	= -Wl,--gc-sections
TARGET_ARCH	= -mmcu=$(AVR)

all:		$(MAIN).elf

$(MAIN).elf:	$(OBJECTS)
	$(LINK.o) -o $@ $(OBJECTS)

$(OBJECTS):	$(HFILES) Makefile

clean:
	rm -f $(OBJECTS) $(MAIN).elf

size:		$(MAIN).elf
	$(TOOLS)/avr-size $<

disasm:		$(MAIN).elf
	$(TOOLS)/avr-objdump -S $<

flash:		$(MAIN).elf
	$(FLASH_CMD)$<
