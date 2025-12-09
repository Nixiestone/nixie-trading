"""
MT5 Auto-Execution Module
Automatically executes signals in MetaTrader 5 (with enable/disable feature)
"""

import MetaTrader5 as mt5
from typing import Dict, Optional
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MT5AutoExecutor:
    """Handles automatic trade execution in MT5"""
    
    def __init__(self, mt5_connection, config):
        self.mt5 = mt5_connection
        self.config = config
        self.enabled = False  # Default: OFF for safety
        self.active_positions = {}  # {signal_id: ticket}
        
    def enable(self):
        """Enable auto-execution"""
        self.enabled = True
        logger.info("MT5 Auto-Execution ENABLED")
    
    def disable(self):
        """Disable auto-execution"""
        self.enabled = False
        logger.info("MT5 Auto-Execution DISABLED")
    
    def is_enabled(self) -> bool:
        """Check if auto-execution is enabled"""
        return self.enabled
    
    async def execute_signal(self, signal: Dict) -> Optional[int]:
        """
        Execute signal in MT5
        Returns: MT5 ticket number or None if failed
        """
        if not self.enabled:
            logger.info("Auto-execution disabled - signal NOT executed")
            return None
        
        try:
            symbol = signal['symbol']
            direction = signal['direction']
            entry_type = signal['entry_type']
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            take_profit = signal['take_profit']
            
            # Calculate lot size based on risk
            account_balance = self.mt5.get_account_balance()
            lot_size = await self.mt5.calculate_lot_size(
                symbol,
                self.config.MAX_RISK_PERCENT,
                signal['sl_pips'],
                account_balance
            )
            
            # Determine order type
            if entry_type == 'MARKET':
                ticket = await self._place_market_order(
                    symbol, direction, lot_size, stop_loss, take_profit
                )
            elif entry_type in ['BUY_LIMIT', 'SELL_LIMIT']:
                ticket = await self._place_limit_order(
                    symbol, direction, entry_price, lot_size, stop_loss, take_profit
                )
            elif entry_type in ['BUY_STOP', 'SELL_STOP']:
                ticket = await self._place_stop_order(
                    symbol, direction, entry_price, lot_size, stop_loss, take_profit
                )
            else:
                logger.error(f"Unknown order type: {entry_type}")
                return None
            
            if ticket:
                self.active_positions[signal['signal_id']] = ticket
                logger.info(f"✅ Trade executed: {symbol} {direction} {entry_type} | Ticket: {ticket}")
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}", exc_info=True)
            return None
    
    async def _place_market_order(self, symbol: str, direction: str, 
                                   lot_size: float, sl: float, tp: float) -> Optional[int]:
        """Place market order"""
        try:
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Symbol {symbol} not found")
                return None
            
            # Prepare order
            order_type = mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL
            price = symbol_info.ask if direction == 'BUY' else symbol_info.bid
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 234000,
                "comment": f"NIXIE_BOT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order failed: {result.retcode} - {result.comment}")
                return None
            
            logger.info(f"Market order executed: {symbol} {direction} | Ticket: {result.order}")
            return result.order
            
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None
    
    async def _place_limit_order(self, symbol: str, direction: str, entry: float,
                                  lot_size: float, sl: float, tp: float) -> Optional[int]:
        """Place limit order"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Symbol {symbol} not found")
                return None
            
            order_type = mt5.ORDER_TYPE_BUY_LIMIT if direction == 'BUY' else mt5.ORDER_TYPE_SELL_LIMIT
            
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": entry,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 234000,
                "comment": f"NIXIE_BOT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Limit order failed: {result.retcode} - {result.comment}")
                return None
            
            logger.info(f"Limit order placed: {symbol} {direction} @ {entry} | Ticket: {result.order}")
            return result.order
            
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return None
    
    async def _place_stop_order(self, symbol: str, direction: str, entry: float,
                                 lot_size: float, sl: float, tp: float) -> Optional[int]:
        """Place stop order"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Symbol {symbol} not found")
                return None
            
            order_type = mt5.ORDER_TYPE_BUY_STOP if direction == 'BUY' else mt5.ORDER_TYPE_SELL_STOP
            
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": entry,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 234000,
                "comment": f"NIXIE_BOT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Stop order failed: {result.retcode} - {result.comment}")
                return None
            
            logger.info(f"Stop order placed: {symbol} {direction} @ {entry} | Ticket: {result.order}")
            return result.order
            
        except Exception as e:
            logger.error(f"Error placing stop order: {e}")
            return None
    
    async def close_position(self, signal_id: str) -> bool:
        """Close position by signal ID"""
        if signal_id not in self.active_positions:
            return False
        
        try:
            ticket = self.active_positions[signal_id]
            
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            
            if not position:
                logger.warning(f"Position {ticket} not found (may already be closed)")
                del self.active_positions[signal_id]
                return True
            
            position = position[0]
            
            # Prepare close request
            order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": "NIXIE_BOT_CLOSE",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Position {ticket} closed successfully")
                del self.active_positions[signal_id]
                return True
            else:
                logger.error(f"Failed to close position {ticket}: {result.comment}")
                return False
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    def get_active_positions_count(self) -> int:
        """Get number of active positions"""
        return len(self.active_positions)