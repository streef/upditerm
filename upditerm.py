#!/usr/bin/python3
"""
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
upditerm.py - Connect to a virtual UART on an AVR via UPDI

Copyright 2024 Dick Streefland

This is free software, licensed under the terms of the GNU General
Public License as published by the Free Software Foundation.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import platform
import sys
import argparse
import time
import atexit
import threading
import serial
import serial.tools.list_ports

VERSION         = '1.1'

# Commandline defaults
BAUDRATE        = 921600
ESCAPE          = 0x05          # CTRL-E

# Secondary escape characters
ESC_EXIT        = ord('e')
ESC_RESET       = ord('r')

# Control characters
BS              = 0x08
LF              = 0x0a
CR              = 0x0d
DEL             = 0x7f

# Timeouts
SERIAL_TIMEOUT  = 1.0
IDLE_TIMEOUT    = 0.25

# I/O memory addresses used for a virtual UART
UART_FLAGS      = 0x1e          # GPIOR2
UART_RX         = 0x1f          # GPIOR3
# bit masks for the UART_FLAGS register
FLAG_ENABLE     = 0x01          # UART is enabled
FLAG_RX         = 0x02          # RX buffer full

# UPDI characters
SYNCH           = 0x55
ACK             = 0x40
BREAK           = 0x00

# UPDI instructions
LDS             = 0x00
STS             = 0x40
LDCS            = 0x80
STCS            = 0xc0
KEY             = 0xe0

# UPDI registers & bitmasks
CTRLB           = 0x3
UPDIDIS         = 0x04
CCDETDIS        = 0x08
NACKDIS         = 0x10

ASI_OCD_CTRLA   = 0x4
OCD_STOP        = 0x01
OCD_RUN         = 0x02
OCD_SOR_DIS     = 0x80

ASI_OCD_STATUS  = 0x5
OCD_STOPPED     = 0x01
OCDMV           = 0x10

ASI_KEY_STATUS  = 0x7
OCD             = 0x02
CHIPERASE       = 0x08
NVMPROG         = 0x10
UROWWRITE       = 0x20

ASI_RESET_REQ   = 0x8
RUN             = 0x00
RESET           = 0x59

ASI_CTRLA       = 0x9
UPDICLKSEL16    = 0x01

ASI_SYS_STATUS  = 0xb
LOCKSTATUS      = 0x01
BOOTDONE        = 0x02
UROWPROG        = 0x04
NVMPROG         = 0x08
INSLEEP         = 0x10
RSTSYS          = 0x20

ASI_OCD_MESSAGE = 0xd

# UPDI keys
KEY_NVMPROG     = 'NVMProg '
KEY_CHIPERASE   = 'NVMErase'
KEY_UROW        = 'NVMUs&te'
KEY_OCD         = 'OCD     '

def error(message):
    print(message)
    sys.exit(1)

class SerialPort:
    "Serial port"
    def __init__(self, port, baudrate=BAUDRATE,
                 parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE,
                 halfduplex=False):
        try:
            self.dev = serial.Serial(port, baudrate,
                                     parity=parity,
                                     stopbits=stopbits,
                                     timeout=SERIAL_TIMEOUT)
            self.halfduplex = halfduplex
        except (ValueError, serial.SerialException) as cause:
            error(f'Cannot open serial port: {cause}')
    def send(self, data):
        if TRACING:
            print(f'send: {data.hex(sep=" ")}')
        self.dev.write(data)
        if self.halfduplex:
            echo = self.dev.read(len(data))
            if data != echo:
                error('No echo')
    def recv(self, length):
        data = self.dev.read(length)
        if TRACING:
            print(f'recv: {data.hex(sep=" ")}')
        return data
    def send_break(self):
        current_baudrate = self.dev.baudrate
        self.dev.baudrate = 300
        self.send(bytes([BREAK])) # 10 bits @ 300 baud = 33ms
        self.dev.baudrate = current_baudrate
    def send1(self, byte, blocking=True):
        while True:
            if self.dev.out_waiting == 0:
                self.send(bytes([byte]))
                return True
            if not blocking:
                return False
    def recv1(self, blocking=True):
        while True:
            if self.dev.in_waiting > 0:
                return self.recv(1)[0]
            if not blocking:
                return None

class UPDI:
    "UPDI connection over a serial port"
    def __init__(self, port, baudrate=BAUDRATE):
        self.ser = None
        self.ser = SerialPort(port, min(baudrate, 115200),
                              parity=serial.PARITY_EVEN,
                              stopbits=serial.STOPBITS_TWO,
                              halfduplex=True)
        self.ser.send_break()
        self.ser.send_break()
        self.stcs(CTRLB, CCDETDIS) # disable contention detection
        if baudrate > 115200:
            self.stcs(ASI_CTRLA, UPDICLKSEL16) # switch AVR to 16MHz UPDI clock
            self.ser.dev.baudrate = baudrate   # switch to requested baudrate
    def __del__(self):
        if self.ser:
            try:
                self.stcs(CTRLB, UPDIDIS) # disable UPDI on exit
            except SystemExit:
                pass
    def send(self, data):
        self.ser.send(bytes(data))
    def instr(self, data):
        self.send([SYNCH] + data)
    def recv(self, length):
        data = self.ser.recv(length)
        if len(data) != length:
            error('Short read')
        return data
    def stcs(self, address, value):
        self.instr([STCS | address, value])
    def ldcs(self, address):
        self.instr([LDCS | address])
        byte = self.recv(1)[0]
        return byte
    def sts8(self, address, value):
        self.instr([STS | (0 << 2), address])
        self.recv(1) # ACK
        self.send([value])
        self.recv(1) # ACK
    def lds8(self, address):
        self.instr([LDS | (0 << 2), address])
        return self.recv(1)[0]
    def sib(self):
        self.instr([KEY | (1 << 2) | 2])
        return self.recv(32).decode()
    def reset(self):
        self.stcs(ASI_RESET_REQ, RESET)
        self.stcs(ASI_RESET_REQ, RUN)
        for _ in range(self.ser.dev.baudrate // 12 // 3 // 10): # poll for 0.1 sec
            if not self.ldcs(ASI_SYS_STATUS) & LOCKSTATUS:
                break
    def key(self, key):
        self.instr([KEY] + list(reversed(list(map(ord, key)))))
        status = self.ldcs(ASI_KEY_STATUS)
        if not status:
            error(f'Key "{key}" not accepted')

class SerialUPDI:
    "Virtual serial port over UPDI"
    def __init__(self, port, baudrate=BAUDRATE, reset=False):
        self.updi = None
        self.updi = UPDI(port, baudrate)
        self.updi.key(KEY_OCD)  # switch to OCD mode to enable stop on reset
        if reset:
            self.updi.reset()
        self.updi.sts8(UART_FLAGS, FLAG_ENABLE)
    def __del__(self):
        if self.updi:
            try:
                self.updi.sts8(UART_FLAGS, 0)
            except SystemExit:
                pass
    def send1(self, byte, blocking=True):
        while True:
            flags = self.updi.lds8(UART_FLAGS)
            if not flags & FLAG_RX:
                self.updi.sts8(UART_RX, byte)
                self.updi.sts8(UART_FLAGS, flags | FLAG_RX)
                return True
            if not blocking:
                return False
    def recv1(self, blocking=True):
        while True:
            flags = self.updi.ldcs(ASI_OCD_STATUS)
            # check for a stopped CPU which indicates that there was a RESET
            if flags & OCD_STOPPED:
                self.updi.sts8(UART_FLAGS, FLAG_ENABLE) # reenable UART
                self.updi.stcs(ASI_OCD_CTRLA, OCD_RUN)  # restart CPU
            # check for an OCD message byte
            if flags & OCDMV:
                return self.updi.ldcs(ASI_OCD_MESSAGE)
            if not blocking:
                return None
    def reset(self):
        self.updi.reset()

class Console:
    "Keyboard & Screen"
    def __init__(self, mapkeys=True):
        self.mapkeys = mapkeys
        self.read = sys.stdin.read
        if sys.stdin.isatty():
            if platform.system() == "Windows":
                import msvcrt
                import ctypes
                kernel32 = ctypes.windll.kernel32
                old_mode = ctypes.wintypes.DWORD()
                kernel32.GetConsoleMode(kernel32.GetStdHandle(-10), ctypes.byref(old_mode))
                def cleanup():
                    kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), old_mode)
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), 0)
                def msvcrt_read(_size):
                    return msvcrt.getch()
                self.read = msvcrt_read
            else:
                import termios
                self.fileno = sys.stdin.fileno()
                self.old_attr = termios.tcgetattr(self.fileno)
                def cleanup():
                    termios.tcsetattr(self.fileno, termios.TCSAFLUSH, self.old_attr)
                attr = termios.tcgetattr(self.fileno)
                attr[0] = attr[0] & ~ (termios.IXON | termios.IXOFF | termios.ICRNL)
                attr[3] = attr[3] & ~ (termios.ICANON | termios.ECHO | termios.ISIG)
                attr[6][termios.VMIN] = 1
                attr[6][termios.VTIME] = 0
                termios.tcsetattr(self.fileno, termios.TCSANOW, attr)
            atexit.register(cleanup)
    def get(self):
        byte = self.read(1)
        if not byte:
            return None
        key = ord(byte)
        if self.mapkeys:
            if key == DEL:
                key = BS
            if key == CR:
                key = LF
        return key
    def put(self, byte):
        sys.stdout.write(chr(byte))
        if sys.stdout.isatty() or byte == LF:
            sys.stdout.flush()

class Terminal:
    "Multiplex data between the console and a serial port"
    def __init__(self, console, serport, escape=None, logfile=None):
        self.console = console
        self.serport = serport
        self.escape = escape
        try:
            self.log = logfile and open(logfile, 'a', encoding='ascii')
        except OSError as cause:
            error(f'Cannot open log file: {cause}')
        self.serport_lock = threading.Lock()
        self.reader_busy = threading.Lock()
        self.reader_busy.acquire()
        self.writer_thread = threading.Thread(target=self.writer, daemon=True)
        self.writer_thread.start()
        self.reader_thread = threading.Thread(target=self.reader, daemon=True)
        self.reader_thread.start()
    def writer(self):
        "Copy from console to serial port"
        while True:
            interactive = not self.escape is None
            try:
                key = self.console.get()
                if key is None:
                    with self.reader_busy:  # wait until the reader is idle
                        break
                if key == self.escape:
                    key2 = self.console.get()
                    if key2 == ESC_EXIT:
                        break
                    if key2 == ESC_RESET:
                        with self.serport_lock:
                            self.serport.reset()
                    if key2 != self.escape:
                        continue
                while True:
                    with self.serport_lock:
                        status = self.serport.send1(key, blocking=False)
                    if status or interactive:
                        break
                    time.sleep(0.010)
            except SystemExit:
                pass
    def reader(self):
        "Copy from serial port to console"
        last_byte = None
        last_time = time.time()
        while self.writer_thread.is_alive():
            try:
                with self.serport_lock:
                    byte = self.serport.recv1(blocking=False)
                if byte:
                    self.console.put(byte)
                    last_byte = byte
                    if self.log:
                        self.log.write(chr(byte))
                    last_time = time.time()
                    if not self.reader_busy.locked():
                        self.reader_busy.acquire()
                    continue
                time.sleep(0.010)
                idle = time.time() - last_time
                if idle > IDLE_TIMEOUT:
                    if self.reader_busy.locked():
                        self.reader_busy.release()  # reader is idle
            except SystemExit:
                pass
        if last_byte != 0x0a:
            self.console.put(0x0a)
    def wait(self):
        "Wait for the termination of the writer and reader threads"
        self.writer_thread.join()
        self.reader_thread.join()

def parse_arguments():
    # Use the first available serial port as default
    ports = [p[0] for p in serial.tools.list_ports.comports(include_links=True)]
    if ports:
        port_default = sorted(ports)[0]
        port_nargs = '?'
    else:
        port_default = None
        port_nargs = None
    parser = argparse.ArgumentParser(
        description='Connect to a virtual UART on an AVR via UPDI')
    parser.add_argument('port', default=port_default, nargs=port_nargs,
        help=f'serial port (default: {port_default})')
    parser.add_argument('baudrate', default=BAUDRATE, nargs='?', type=int,
        help=f'baudrate (default: {BAUDRATE})')
    parser.add_argument('-e', metavar='ascii', type=int, default=ESCAPE, choices=range(0,32),
        help=f'escape character (default: {ESCAPE})')
    parser.add_argument('-l', metavar='file',
        help='append output to a log file')
    parser.add_argument('-k', action='store_true',
        help='disable keyboard mappings CR->LF and DEL->BS')
    parser.add_argument('-q', action='store_true',
        help='suppress the initial line showing the escape sequences')
    parser.add_argument('-r', action='store_true',
        help='reset the AVR device before connecting')
    parser.add_argument('-i', action='store_true',
        help='show the AVR System Information Block (SIB)')
    parser.add_argument('-t', action='store_true',
        help='enable a trace of the serial communication')
    parser.add_argument('-v', action='store_true',
        help='show the version number')
    arg = parser.parse_args()
    # Also accept a baudrate without a port name
    if arg.port and arg.port.isnumeric():
        arg.baudrate = int(arg.port)
        if not port_default:
            error('No default port')
        arg.port = port_default
    return arg

def main(arg):
    try:
        if arg.v:
            print(VERSION)
        elif arg.i:
            updi = UPDI(arg.port, arg.baudrate)
            print(updi.sib())
        else:
            if sys.stdin.isatty():
                escape = arg.e
                mapkeys = not arg.k
                showhelp = not arg.q
            else:
                escape = None
                mapkeys = False
                showhelp = False
            serport = SerialUPDI(arg.port, arg.baudrate, arg.r)
            console = Console(mapkeys=mapkeys)
            if showhelp:
                esc = f'^{0x40+arg.e:c}'
                print(f'>>>  Exit: {esc}+e  Reset: {esc}+r  {esc}: {esc}+{esc}', file=sys.stderr)
            terminal = Terminal(console, serport, escape=escape, logfile=arg.l)
            terminal.wait()
    except SystemExit:
        sys.exit(1)

if __name__ == '__main__':
    arguments = parse_arguments()
    TRACING = arguments.t
    main(arguments)
