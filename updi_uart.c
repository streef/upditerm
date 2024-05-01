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
#define	UART_FLAGS	GPIOR2
#define	UART_RX		GPIOR3

// Bit masks for the flags register
#define	FLAG_ENABLE	0x01		// UART is enabled
#define	FLAG_RX		0x02		// RX buffer full

// Undocumented registers for OCD messaging, used for transmitting
#define	SYSCFG_OCDM	_SFR_MEM8(0x0F18)
#define	SYSCFG_OCDMS	_SFR_MEM8(0x0F19)

// ----------------------------------------------------------------------
// Check whether the UART has been enabled by upditerm
// ----------------------------------------------------------------------
extern	_Bool	updi_uart_enabled	( void )
{
	return (UART_FLAGS & FLAG_ENABLE);
}

// ----------------------------------------------------------------------
// Transmit a byte
// ----------------------------------------------------------------------
extern	void	updi_uart_tx		( uint8_t byte )
{
	while	( UART_FLAGS & FLAG_ENABLE )
	{
		if	( ! SYSCFG_OCDMS )
		{
			SYSCFG_OCDM = byte;
			break;
		}
	}
}

// ----------------------------------------------------------------------
// Check if a byte is available in the input buffer
// ----------------------------------------------------------------------
extern	_Bool	updi_uart_rx_poll	( void )
{
	return (UART_FLAGS & FLAG_RX);
}

// ----------------------------------------------------------------------
// Receive a byte
// ----------------------------------------------------------------------
extern	uint8_t	updi_uart_rx		( void )
{
	uint8_t	byte;

	while	( ! (UART_FLAGS & FLAG_RX) )
	{
	}
	byte = UART_RX;
	UART_FLAGS &= ~ FLAG_RX;
	return byte;
}
