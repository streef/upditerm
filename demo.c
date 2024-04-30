// ======================================================================
// Demo program for upditerm
//
// Control a breathing LED on WO2, but switch to an interactive mode when
// upditerm connects. In this mode you can use the following keys:
//
//   +  increase the brightness of the LED by 5%
//   -  decrease the brightness of the LED by 5%
//   s  show the chip signature
//   d  dump the contents of the SRAM
//   r  use the watchdog timer to force a RESET
//
// Copyright 2024 Dick Streefland
//
// This is free software, licensed under the terms of the GNU General
// Public License as published by the Free Software Foundation.
// ======================================================================

#include <stdio.h>
#include <avr/io.h>
#include <util/delay.h>
#include "updi_uart.h"
#include "updi_stdio.h"

// 8-pin ATtiny devices have WO2 on PORTA, the others on PORTB
#ifdef	PORTB
#define	WO2_PORT	VPORTB
#define	WO2_PIN		2
#else
#define	WO2_PORT	VPORTA
#define	WO2_PIN		2
#endif

#define	STEP		5		// brightness steps in %

uint8_t	sig[3] __attribute__((address(0x1100)));

// ----------------------------------------------------------------------
// Initialize PWM for the LED
// ----------------------------------------------------------------------
static	void	pwm_init	( void )
{
	WO2_PORT.DIR |= _BV(WO2_PIN);
	TCA0.SINGLE.PER = 99;
	TCA0.SINGLE.CMP2 = 0;
	TCA0.SINGLE.CTRLA = TCA_SINGLE_CLKSEL_DIV256_gc | TCA_SINGLE_ENABLE_bm;
	TCA0.SINGLE.CTRLB = TCA_SINGLE_CMP2EN_bm | TCA_SINGLE_WGMODE_SINGLESLOPE_gc;
}

// ----------------------------------------------------------------------
// Set the duty cycle of the LED as a percentage
// ----------------------------------------------------------------------
static	void	pwm_set		( uint8_t duty )
{
	TCA0.SINGLE.CMP2BUF = duty;
}

// ----------------------------------------------------------------------
// Dump SRAM
// ----------------------------------------------------------------------
static	void	dump		( void )
{
	uint16_t	addr;

	printf( "SRAM size: %u\n", RAMSIZE );
	for	( addr = RAMSTART; addr < RAMSTART + RAMSIZE; addr++ )
	{
		if	( (addr & 15) == 0 )
		{
			printf( "%04x:", addr );
		}
		printf( " %02x", *(uint8_t*)addr );
		if	( (addr & 15) == 15 )
		{
			printf( "\n" );
		}
	}
}

// ----------------------------------------------------------------------
// Main
// ----------------------------------------------------------------------
extern	int	main		( void )
{
	uint8_t	brightness;
	int8_t	dir;
	uint8_t	key;

	updi_stdio_init();	// redirect stdin/stdout
	printf( "\nRESET\n" );
	brightness = 0;
	dir = +1;
	pwm_init();
	pwm_set( brightness );
	while	( 1 )
	{
		if	( ! updi_uart_enabled() )
		{
			if	( brightness == 0 )
			{
				dir = +1;
			}
			else if	( brightness == 100 )
			{
				dir = -1;
			}
			brightness += dir;
			pwm_set( brightness );
			_delay_ms( 20 );
		}
		else if	( updi_uart_rx_poll() )	// avoid blocking on getchar()
		{
			key = getchar();
			switch	( key )
			{
			case '+':	// increase brightness
				if	( brightness <= 100 - STEP )
				{
					brightness += STEP;
				}
				else
				{
					brightness = 100;
				}
				pwm_set( brightness );
				break;
			case '-':	// decrease brightness
				if	( brightness >= STEP )
				{
					brightness -= STEP;
				}
				else
				{
					brightness = 0;
				}
				pwm_set( brightness );
				break;
			case 's':	// show chip signature
				printf( "signature: %02x %02x %02x\n", sig[0], sig[1], sig[2] );
				break;
			case 'd':	// dump SRAM
				dump();
				break;
			case 'r':
				CCP = 0xd8;
				WDT.CTRLA = WDT_PERIOD_256CLK_gc;	// 0.256 sec
				break;
			default:
				printf( "unrecognized key: %02x\n", key );
				break;
			}
			printf( "%3u%%\n", brightness );
		}
	}
}
