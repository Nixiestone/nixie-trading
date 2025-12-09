"""
Multi-User MT5 Auto-Executor
Executes trades on each user's own MT5 accounts
"""

import MetaTrader5 as mt5
from typing import Dict, Optional, List
from datetime import datetime
import asyncio
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MultiUserMT5Executor:
    """Handles trade execution across multiple user accounts"""
    
    def __init__(self, account_manager, config):
        self.account_manager = account_manager
        self.config = config
        self.active_connections = {}  # {account_id: connection_info}
        self.user_positions = {}  # {user_id: {signal_id: [tickets]}}
        
    async def execute_signal_for_all_users(self, signal: Dict) -> Dict:
        """
        Execute signal on all enabled user accounts
        Returns: {user_id: {account_id: ticket}}
        """
        results = {}
        
        # Get all enabled accounts across all users
        all_enabled = self.account_manager.get_all_enabled_accounts()
        
        if not all_enabled:
            logger.info("No enabled accounts for execution")
            return results
        
        # Execute on each user's accounts
        for user_id, accounts in all_enabled.items():
            user_results = {}
            
            for account in accounts:
                try:
                    # Execute trade
                    ticket = await self._execute_on_account(user_id, account, signal)
                    
                    if ticket:
                        user_results[account['account_id']] = ticket
                        
                        # Track position
                        if user_id not in self.user_positions:
                            self.user_positions[user_id] = {}
                        if signal['signal_id'] not in self.user_positions[user_id]:
                            self.user_positions[user_id][signal['signal_id']] = []
                        
                        self.user_positions[user_id][signal['signal_id']].append({
                            'account_id': account['account_id'],
                            'ticket': ticket,
                            'account_nickname': account['nickname']
                        })
                        
                        # Increment trade count
                        self.account_manager.increment_trade_count(user_id, account['account_id'])
                        
                        logger.info(f"Trade executed for user {user_id} on {account['nickname']}: Ticket {ticket}")
                
                except Exception as e:
                    logger.error(f"Error executing on account {account['account_id']}: {e}")
                    user_results[account['account_id']] = None
            
            if user_results:
                results[user_id] = user_results
        
        return results
    
    async def _execute_on_account(self, user_id: str, account: Dict, signal: Dict) -> Optional[int]:
        """Execute trade on a specific user account"""
        try:
            # Get account credentials
            credentials = self.account_manager.get_account_credentials(
                user_id, 
                account['account_id']
            )
            
            if not credentials:
                logger.error(f"Could not get credentials for account {account['account_id']}")
                return None
            
            # Connect to this specific account
            if not await self._connect_to_account(credentials, account['account_id']):
                logger.error(f"Failed to connect to account {account['login']}")
                return None
            
            # Get account balance
            account_info = mt5.account_info()
            if not account_info:
                logger.error(f"Could not get account info for {account['login']}")
                return None
            
            balance = account_info.balance
            
            # Calculate lot size based on this account's balance
            lot_size = await self._calculate_lot_size(
                signal['symbol'],
                self.config.MAX_RISK_PERCENT,
                signal['sl_pips'],
                balance
            )
            
            # Execute based on order type
            entry_type = signal['entry_type']
            direction = signal['direction']
            
            if entry_type == 'MARKET':
                ticket = await self._place_market_order(
                    signal['symbol'],
                    direction,
                    lot_size,
                    signal['stop_loss'],
                    signal['take_profit'],
                    account['nickname']
                )
            elif entry_type in ['BUY_LIMIT', 'SELL_LIMIT']:
                ticket = await self._place_limit_order(
                    signal['symbol'],
                    direction,
                    signal['entry_price'],
                    lot_size,
                    signal['stop_loss'],
                    signal['take_profit'],
                    account['nickname']
                )
            elif entry_type in ['BUY_STOP', 'SELL_STOP']:
                ticket = await self._place_stop_order(
                    signal['symbol'],
                    direction,
                    signal['entry_price'],
                    lot_size,
                    signal['stop_loss'],
                    signal['take_profit'],
                    account['nickname']
                )
            else:
                logger.error(f"Unknown order type: {entry_type}")
                return None
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error executing on account: {e}", exc_info=True)
            return None
        finally:
            # Always shutdown MT5 connection after trade
            try:
                mt5.shutdown()
            except:
                pass
    
    async def _connect_to_account(self, credentials: Dict, account_id: str) -> bool:
        """Connect to a specific MT5 account"""
        try:
            # Initialize MT5
            if not mt5.initialize():
                logger.error(f"MT5 initialization failed for account {account_id}")
                return False
            
            # Login to account
            authorized = mt5.login(
                login=credentials['login'],
                password=credentials['password'],
                server=credentials['server'],
                timeout=60000
            )
            
            if not authorized:
                error = mt5.last_error()
                logger.error(f"MT5 login failed for {credentials['login']}: {error}")
                mt5.shutdown()
                return False
            
            logger.info(f"Connected to MT5 account: {credentials['login']}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to account: {e}")
            return False
    
    async def _calculate_lot_size(self, symbol: str, risk_percent: float, 
                                   stop_loss_pips: float, account_balance: float) -> float:
        """Calculate lot size based on account balance and risk"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            
            if not symbol_info:
                logger.warning(f"Could not get symbol info for {symbol}, using default 0.01")
                return 0.01
            
            # Risk amount
            risk_amount = account_balance * (risk_percent / 100)
            
            # Get point value
            point = symbol_info.point
            contract_size = symbol_info.trade_contract_size
            
            # Calculate pip value
            if 'JPY' in symbol:
                pip_value = (point * 100) * contract_size
            else:
                pip_value = point * contract_size
            
            # Calculate lot size
            lot_size = risk_amount / (stop_loss_pips * pip_value)
            
            # Round to volume step
            volume_step = symbol_info.volume_step
            lot_size = round(lot_size / volume_step) * volume_step
            
            # Ensure within limits
            lot_size = max(symbol_info.volume_min, 
                          min(lot_size, symbol_info.volume_max))
            
            logger.info(f"Calculated lot size: {lot_size} (Risk: {risk_percent}%, Balance: ${account_balance:.2f})")
            
            return lot_size
            
        except Exception as e:
            logger.error(f"Error calculating lot size: {e}")
            return 0.01
    
    async def _place_market_order(self, symbol: str, direction: str, lot_size: float,
                                   sl: float, tp: float, account_name: str) -> Optional[int]:
        """Place market order"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return None
            
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
                "comment": f"NIXIE_{account_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Market order failed on {account_name}: {result.comment}")
                return None
            
            return result.order
            
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None
    
    async def _place_limit_order(self, symbol: str, direction: str, entry: float,
                                  lot_size: float, sl: float, tp: float, 
                                  account_name: str) -> Optional[int]:
        """Place limit order"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
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
                "comment": f"NIXIE_{account_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Limit order failed on {account_name}: {result.comment}")
                return None
            
            return result.order
            
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return None
    
    async def _place_stop_order(self, symbol: str, direction: str, entry: float,
                                 lot_size: float, sl: float, tp: float,
                                 account_name: str) -> Optional[int]:
        """Place stop order"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
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
                "comment": f"NIXIE_{account_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Stop order failed on {account_name}: {result.comment}")
                return None
            
            return result.order
            
        except Exception as e:
            logger.error(f"Error placing stop order: {e}")
            return None
    
    def get_user_positions(self, user_id: str, signal_id: str) -> List[Dict]:
        """Get positions for a user's signal"""
        if user_id not in self.user_positions:
            return []
        
        return self.user_positions[user_id].get(signal_id, [])
    
    def get_total_executions(self) -> Dict:
        """Get statistics on executions"""
        total_users = len(self.user_positions)
        total_positions = sum(
            len(signals) 
            for signals in self.user_positions.values()
        )
        
        return {
            'users_with_positions': total_users,
            'total_positions': total_positions
        }