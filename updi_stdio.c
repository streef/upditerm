// ======================================================================
// Redirect stdio/stdout to the updi_uart.c module
//
// Copyright 2024 Dick Streefland
//
// This is free software, licensed under the terms of the GNU General
// Public License as published by the Free Software Foundation.
// ======================================================================

#include <stdio.h>
#include "updi_uart.h"
#include "updi_stdio.h"

// ----------------------------------------------------------------------
// Replacement for getchar()
// ----------------------------------------------------------------------
static	int	updi_getchar	( FILE* stream )
{
	(void) stream;
	return updi_uart_rx();
}

// ----------------------------------------------------------------------
// Replacement for putchar()
// ----------------------------------------------------------------------
static	int	updi_putchar	( char c, FILE* stream )
{
	(void) stream;
	updi_uart_tx( c );
	return c;
}

static	FILE	stream = FDEV_SETUP_STREAM(updi_putchar, updi_getchar, _FDEV_SETUP_RW);

// ----------------------------------------------------------------------
// Redirect stdio/stdout to the functions of the updi_uart.c module
// ----------------------------------------------------------------------
extern	void	updi_stdio_init	( void )
{
	stdin  = & stream;
	stdout = & stream;
}
