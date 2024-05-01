// ======================================================================
// Virtual UART to be used in combination with upditerm
//
// Copyright 2024 Dick Streefland
//
// This is free software, licensed under the terms of the GNU General
// Public License as published by the Free Software Foundation.
// ======================================================================

#ifdef __cplusplus
extern "C"
{
#endif

extern	_Bool	updi_uart_enabled	( void );
extern	void	updi_uart_tx		( uint8_t byte );
extern	_Bool	updi_uart_rx_poll	( void );
extern	uint8_t	updi_uart_rx		( void );

#ifdef __cplusplus
}
#endif
