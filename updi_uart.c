// ======================================================================
// Virtual UART to be used in combination with upditerm
//
// Copyright 2024 Dick Streefland
//
// This is free software, licensed under the terms of the GNU General
// Public License as published by the Free Software Foundation.
// ======================================================================

#include <stdio.h>
#include <avr/io.h>
#include "updi_uart.h"

// I/O registers for the virtual UART
#define	RX_FLAGS	GPIOR0
#define	RX		GPIOR1
#define	TX_FLAGS	GPIOR2
#define	TX		GPIOR3

// Bit masks for the flags registers
#define	ENABLE		0x02
#define	FULL		0x01

// ----------------------------------------------------------------------
// Enable the receiver, allowing upditerm to send data
// ----------------------------------------------------------------------
extern	void	updi_uart_rx_enable	( void )
{
	RX_FLAGS |= ENABLE;
}

// ----------------------------------------------------------------------
// Disable the receiver
// ----------------------------------------------------------------------
extern	void	updi_uart_rx_disable	( void )
{
	RX_FLAGS &= ~ ENABLE;
}

// ----------------------------------------------------------------------
// Check if a byte is available in the input buffer
// ----------------------------------------------------------------------
extern	_Bool	updi_uart_rx_poll	( void )
{
	return RX_FLAGS == (ENABLE | FULL);
}

// ----------------------------------------------------------------------
// Receive a byte
// ----------------------------------------------------------------------
extern	uint8_t	updi_uart_rx		( void )
{
	uint8_t	byte;

	while	( ! updi_uart_rx_poll() )
	{
	}
	byte = RX;
	RX_FLAGS &= ~ FULL;
	return byte;
}

// ----------------------------------------------------------------------
// Check whether the transmitter has been enabled by upditerm
// ----------------------------------------------------------------------
extern	_Bool	updi_uart_tx_enabled	( void )
{
	return (TX_FLAGS & ENABLE);
}

// ----------------------------------------------------------------------
// Transmit a byte
// ----------------------------------------------------------------------
extern	void	updi_uart_tx		( uint8_t byte )
{
	while	( TX_FLAGS & ENABLE )
	{
		if	( ! (TX_FLAGS & FULL) )
		{
			TX = byte;
			TX_FLAGS |= FULL;
			break;
		}
	}
}
