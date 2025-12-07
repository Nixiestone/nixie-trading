"""
MetaTrader 5 Connection Handler for Exness Broker
"""

import MetaTrader5 as mt5
import asyncio
from datetime import datetime
import pandas as pd
from typing import Optional, Dict, List
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MT5Connection:
    """Handles MT5 connection and data retrieval"""
    
    def __init__(self, config):
        self.config = config
        self.connected = False
        self.account_info = None
        
    async def connect(self) -> bool:
        """Connect to MT5 terminal"""
        try:
            # Initialize MT5
            if not mt5.initialize():
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
            
            # Login to account
            authorized = mt5.login(
                login=self.config.MT5_LOGIN,
                password=self.config.MT5_PASSWORD,
                server=self.config.MT5_SERVER,
                timeout=self.config.MT5_TIMEOUT
            )
            
            if not authorized:
                logger.error(f"MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                return False
            
            # Get account info
            self.account_info = mt5.account_info()
            
            if self.account_info is None:
                logger.error("Failed to get account info")
                mt5.shutdown()
                return False
            
            self.connected = True
            logger.info(f"Connected to MT5 - Account: {self.account_info.login}, "
                       f"Balance: {self.account_info.balance}, "
                       f"Server: {self.account_info.server}")
            
            return True
            
        except Exception as e:
            logger.error(f"MT5 connection error: {e}", exc_info=True)
            return False
    
    async def disconnect(self):
        """Disconnect from MT5"""
        try:
            if self.connected:
                mt5.shutdown()
                self.connected = False
                logger.info("Disconnected from MT5")
        except Exception as e:
            logger.error(f"Error disconnecting MT5: {e}")
    
    async def get_rates(self, symbol: str, timeframe: str, count: int = 500) -> Optional[pd.DataFrame]:
        """Get historical rates for symbol"""
        try:
            if not self.connected:
                logger.error("MT5 not connected")
                return None
            
            # Convert timeframe string to MT5 constant
            tf_map = {
                '1': mt5.TIMEFRAME_M1,
                '5': mt5.TIMEFRAME_M5,
                '15': mt5.TIMEFRAME_M15,
                '30': mt5.TIMEFRAME_M30,
                '60': mt5.TIMEFRAME_H1,
                '240': mt5.TIMEFRAME_H4,
                '1440': mt5.TIMEFRAME_D1
            }
            
            timeframe_mt5 = tf_map.get(timeframe, mt5.TIMEFRAME_M5)
            
            # Get rates
            rates = mt5.copy_rates_from_pos(symbol, timeframe_mt5, 0, count)
            
            if rates is None or len(rates) == 0:
                logger.error(f"Failed to get rates for {symbol}: {mt5.last_error()}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting rates for {symbol}: {e}", exc_info=True)
            return None
    
    async def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information"""
        try:
            if not self.connected:
                return None
            
            symbol_info = mt5.symbol_info(symbol)
            
            if symbol_info is None:
                logger.error(f"Failed to get info for {symbol}")
                return None
            
            return {
                'name': symbol_info.name,
                'point': symbol_info.point,
                'digits': symbol_info.digits,
                'spread': symbol_info.spread,
                'trade_contract_size': symbol_info.trade_contract_size,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'bid': symbol_info.bid,
                'ask': symbol_info.ask
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    async def get_tick(self, symbol: str) -> Optional[Dict]:
        """Get latest tick for symbol"""
        try:
            if not self.connected:
                return None
            
            tick = mt5.symbol_info_tick(symbol)
            
            if tick is None:
                return None
            
            return {
                'time': datetime.fromtimestamp(tick.time),
                'bid': tick.bid,
                'ask': tick.ask,
                'last': tick.last,
                'volume': tick.volume
            }
            
        except Exception as e:
            logger.error(f"Error getting tick for {symbol}: {e}")
            return None
    
    async def calculate_lot_size(self, symbol: str, risk_percent: float, 
                                 stop_loss_pips: float, account_balance: float) -> float:
        """Calculate lot size based on risk parameters"""
        try:
            symbol_info = await self.get_symbol_info(symbol)
            
            if not symbol_info:
                return 0.01  # Default minimum
            
            # Risk amount in account currency
            risk_amount = account_balance * (risk_percent / 100)
            
            # Get point value
            point = symbol_info['point']
            contract_size = symbol_info['trade_contract_size']
            
            # Calculate pip value
            if 'JPY' in symbol:
                pip_value = (point * 100) * contract_size
            else:
                pip_value = point * contract_size
            
            # Calculate lot size
            lot_size = risk_amount / (stop_loss_pips * pip_value)
            
            # Round to volume step
            volume_step = symbol_info['volume_step']
            lot_size = round(lot_size / volume_step) * volume_step
            
            # Ensure within limits
            lot_size = max(symbol_info['volume_min'], 
                          min(lot_size, symbol_info['volume_max']))
            
            logger.info(f"Calculated lot size for {symbol}: {lot_size} "
                       f"(Risk: {risk_percent}%, SL: {stop_loss_pips} pips)")
            
            return lot_size
            
        except Exception as e:
            logger.error(f"Error calculating lot size: {e}", exc_info=True)
            return 0.01
    
    def get_account_balance(self) -> float:
        """Get current account balance"""
        try:
            if not self.connected:
                return 0.0
            
            account_info = mt5.account_info()
            return account_info.balance if account_info else 0.0
            
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return 0.0
    
    def get_account_equity(self) -> float:
        """Get current account equity"""
        try:
            if not self.connected:
                return 0.0
            
            account_info = mt5.account_info()
            return account_info.equity if account_info else 0.0
            
        except Exception as e:
            logger.error(f"Error getting account equity: {e}")
            return 0.0
    
    async def check_connection(self) -> bool:
        """Check if MT5 connection is still alive"""
        try:
            if not self.connected:
                return False
            
            # Try to get account info
            account_info = mt5.account_info()
            
            if account_info is None:
                self.connected = False
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            self.connected = False
            return False