// ======================================================================
// Virtual UART to be used in combination with upditerm
//
// Copyright 2024 Dick Streefland
//
// This is free software, licensed under the terms of the GNU General
// Public License as published by the Free Software Foundation.
// ======================================================================

extern	void	updi_uart_rx_enable	( void );
extern	void	updi_uart_rx_disable	( void );
extern	_Bool	updi_uart_rx_poll	( void );
extern	uint8_t	updi_uart_rx		( void );
extern	_Bool	updi_uart_tx_enabled	( void );
extern	void	updi_uart_tx		( uint8_t byte );
