# Connect to a virtual UART on an AVR via UPDI

## Upditerm

Upditerm is a terminal program similar to miniterm, but instead of
connecting directly to a serial port, it uses a serial port wired as a
UPDI interface to access a virtual UART on the target CPU.  You can
use upditerm to interact with a program on an AVR microcontroller
using only the UPDI interface. This means that you don't need any
additional I/O pins and you don't need to rewire the serial interface
when switching between flashing and debugging. It is therefor
particularly useful for low pincount ATtiny devices with a UPDI
interface. Upditerm is written in Python and runs on Linux and
Windows. It will probably also run on macOS, but I have not tested
that.

You can connect to the target CPU without disturbing the program,
although there is an option to reset the CPU when connecting. The
transmitter of the virtual UART is enabled when upditerm connects and
disabled on exit so debugging output will not slow down the program
when upditerm is not connected.

The transfer speed will be quite a bit lower than with a direct serial
connection, as several UPDI commands are needed to transfer a single
byte. Receiving a byte requires 6 bytes over the serial line, and
sending a byte requires 16 bytes. According to the datasheet, the
maximum serial port speed supported by the UPDI interface is 0.9 Mbps,
but the serial port hardware may have a lower limit. I've successfully
used upditerm with a CP2102 based USB to serial converter at its
maximum speed of 921600 baud. You can quickly check the UPDI
connection with the -i option, which shows the System Information
Block (SIB) of the AVR.

## Virtual UART

The virtual UART uses (undocumented) OCD messaging to transmit data
and two GPIORx I/O registers to receive data.  These registers are
located in the range 0x00..0x3F and can be accessed via UPDI without
halting the CPU.  Receiving a byte via OCD messaging is considerably
faster than fetching a byte from the GPIORx registers and can be done
with 6 instead of 14 bytes of UPDI communication.

The UPDI interface is switched to the (undocumented) OCD mode to
enable stop on reset. This allows upditerm to detect a reset of the
CPU and reenable the UART before restarting the CPU.  When you use the
option to reset the CPU when connecting, stopping the CPU after reset
avoids a race between upditerm enabling the UART and the first output
from the AVR.  It also allows upditerm to reenable the UART when a
reset occurs later.

## Usage

```
usage: upditerm.py [-h] [-e ascii] [-l file] [-k] [-q] [-r] [-i] [-t] [-v] [port] [baudrate]

Connect to a virtual UART on an AVR via UPDI

positional arguments:
  port        serial port (default: /dev/UPDI)
  baudrate    baudrate (default: 921600)

options:
  -h, --help  show this help message and exit
  -e ascii    escape character (default: 5)
  -l file     append output to a log file
  -k          disable keyboard mappings CR->LF and DEL->BS
  -q          suppress the initial line showing the escape sequences
  -r          reset the AVR device before connecting
  -i          show the AVR System Information Block (SIB)
  -t          enable a trace of the serial communication
  -v          show the version number
```

The default for the serial port is the first available serial port.
Instead of using upditerm interactively, you can redirect the input
and/or output. When the input is redirected, the escape character is
disabled and the -k and -q options are implicitly enabled. In this
case, upditerm will terminate when the input is exhausted and the
receiver is idle for 0.25 seconds. For interactive use, upditerm will
not block on unprocessed input so that you can always use escape
sequences to terminate the program or reset the AVR.

## Demo program

I've included a small program that demonstrates how the virtual UART
can be used. It uses a `updi_uart.c` module that accesses the
virtual UART and a `updi_stdio.c` module that redirects the
stdin/stdout streams to the virtual UART. The demo program itself
implements a breathing LED that can be controlled interactively with
the `+` and `-` keys once you connect to the device via upditerm.

Examples:

```
$ upditerm.py /dev/UPDI
>>>  Exit: ^E+e  Reset: ^E+r  ^E: ^E+^E
 13%
 18%
 23%
$ echo -n s++-- | upditerm.py -r /dev/UPDI

RESET
signature: 1e 92 23
  0%
  5%
 10%
  5%
  0%
```

## Prerequisites

The upditerm program requires the `pyserial` Python module, which
is distributed as a separate `python3-serial` package in Ubuntu.
To build the demo program, you will need recent versions of gcc,
binutils and libc for the AVR that support the newer devices with
UPDI.  Unfortunately, the `gcc-avr`, `binutils-avr` and `avr-libc`
packages in Ubuntu have not been updated for a long time. Even the
packages in Ubuntu 24.04 still don't support the newer AVR devices,
so I ended up building them myself following the instructions from
this blog:

    https://blog.zakkemble.net/avr-gcc-builds/

and installing the result in `/usr/local/avr-gcc-13.2.0-x64-linux`.
To flash the demo program, you need a recent version of `avrdude` with
support for the `serialupdi` programmer protocol, which was added in
version 7.0.

## UPDI interface

You can easily build a UPDI interface from a USB-to-serial cable.
Simply connect the GND wire of the cable (usually black) to GND of the
AVR, optionally power the AVR with the VCC wire (usually red), connect
the RX wire (usually white) to the UPDI pin and connect the TX wire
(usually green) with a 1K resistor to the RX wire.

## License

Upditerm is free software, licensed under the terms of the GNU General
Public License as published by the Free Software Foundation.
