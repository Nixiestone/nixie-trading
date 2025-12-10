"""
Nixie's Trading Bot - Updated Main Entry Point
COMPLETE VERSION with Multi-User Account Management
"""

import sys
import os
import time
import asyncio
from datetime import datetime
from colorama import init, Fore, Style
from pyfiglet import Figlet

# Create directories
def ensure_directories():
    """Ensure all required directories exist"""
    directories = ['data', 'logs', 'models']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

ensure_directories()
init(autoreset=True)

from src.config.settings import Config
from src.core.market_analyzer import MarketAnalyzer
from src.core.signal_generator import SignalGenerator
from src.core.ml_engine import MLEngine
from src.telegram.bot_handler import TelegramBotHandler
from src.mt5.connection import MT5Connection
from src.mt5.multi_user_executor import MultiUserMT5Executor
from src.mt5.auto_executor import MT5AutoExecutor
from src.core.user_account_manager import MT5AccountManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class NixieTradingBot:
    """Main trading bot with multi-user account management"""
    
    def __init__(self):
        self.config = Config()
        self.running = False
        self.mt5_connection = None
        self.market_analyzer = None
        self.signal_generator = None
        self.ml_engine = None
        self.telegram_handler = None
        self.account_manager = None
        self.multi_user_executor = None
        self.last_hourly_update = None
        self.last_trade_check = None
        
    def display_banner(self):
        """Display animated startup banner"""
        banner_text = "NIXIE'S TRADING BOT"
        fig = Figlet(font='slant')
        ascii_banner = fig.renderText(banner_text)
        
        colors = [Fore.CYAN, Fore.BLUE, Fore.MAGENTA, Fore.CYAN]
        
        for color in colors:
            sys.stdout.write('\033[2J\033[H')
            print(color + Style.BRIGHT + ascii_banner)
            print(Fore.WHITE + Style.BRIGHT + "=" * 80)
            print(Fore.GREEN + Style.BRIGHT + "Multi-User Institutional Trading System")
            print(Fore.YELLOW + "Author: Blessing Omoregie (Nixiestone)")
            print(Fore.WHITE + "=" * 80)
            time.sleep(0.3)
        
        print(Fore.GREEN + "\n[SYSTEM] Initializing trading systems...")
        time.sleep(1)
    
    async def initialize(self):
        """Initialize all bot components"""
        try:
            logger.info("Starting Nixie's Trading Bot initialization...")
            
            # Validate configuration
            print(Fore.CYAN + "[CONFIG] Validating configuration...")
            try:
                self.config.validate()
                print(Fore.GREEN + "[CONFIG] Configuration valid")
            except ValueError as e:
                print(Fore.RED + f"[ERROR] Configuration invalid: {e}")
                return False
            
            # Initialize MT5 connection (for market analysis)
            print(Fore.CYAN + "[MT5] Connecting to MetaTrader 5...")
            self.mt5_connection = MT5Connection(self.config)
            if not await self.mt5_connection.connect():
                print(Fore.RED + "[ERROR] Failed to connect to MT5")
                return False
            print(Fore.GREEN + "[MT5] Connected successfully")
            
            # Initialize account manager
            print(Fore.CYAN + "[ACCOUNTS] Initializing user account manager...")
            self.account_manager = MT5AccountManager(self.config)
            account_stats = self.account_manager.get_total_accounts()
            print(Fore.GREEN + f"[ACCOUNTS] Loaded {account_stats['total_accounts']} accounts for {account_stats['total_users']} users")
            
            # Initialize multi-user executor
            print(Fore.CYAN + "[EXECUTOR] Initializing multi-user execution engine...")
            self.multi_user_executor = MultiUserMT5Executor(self.account_manager, self.config)
            print(Fore.GREEN + "[EXECUTOR] Multi-user executor ready")
            
            # Initialize market analyzer
            print(Fore.CYAN + "[ANALYZER] Initializing market analysis engine...")
            self.market_analyzer = MarketAnalyzer(self.mt5_connection, self.config)
            print(Fore.GREEN + "[ANALYZER] Market analyzer ready")
            
            # Initialize ML engine
            print(Fore.CYAN + "[ML] Loading machine learning engine...")
            self.ml_engine = MLEngine(self.config)
            await self.ml_engine.initialize()
            print(Fore.GREEN + "[ML] Machine learning engine loaded")
            
            # Initialize signal generator (ENHANCED VERSION)
            print(Fore.CYAN + "[SIGNAL] Initializing enhanced signal generation system...")
            self.signal_generator = SignalGenerator(
                self.market_analyzer,
                self.ml_engine,
                self.config
            )
            print(Fore.GREEN + "[SIGNAL] Signal generator ready with:")
            print(Fore.GREEN + "  ✓ Duplicate prevention")
            print(Fore.GREEN + "  ✓ Auto CSV export")
            print(Fore.GREEN + "  ✓ Trade monitoring")
            print(Fore.GREEN + "  ✓ Win rate tracking")
            
            # Initialize Telegram handler
            print(Fore.CYAN + "[TELEGRAM] Starting Telegram bot...")
            self.telegram_handler = TelegramBotHandler(self.config, self)
            
            try:
                await self.telegram_handler.initialize()
                print(Fore.GREEN + "[TELEGRAM] Telegram bot started")
            except Exception as e:
                print(Fore.RED + f"[ERROR] Telegram initialization failed: {e}")
                return False
            
            # Send startup notification
            try:
                await self.telegram_handler.broadcast_message(
                    self._format_startup_message()
                )
                print(Fore.GREEN + "[TELEGRAM] Startup notification sent")
            except Exception as e:
                logger.error(f"Failed to send startup notification: {e}")
            
            logger.info("Bot initialization completed successfully")
            print(Fore.GREEN + Style.BRIGHT + "\n[SYSTEM] All systems operational. Bot is now active.\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            print(Fore.RED + f"[ERROR] Initialization failed: {e}")
            return False
    
    async def run(self):
        """Main bot loop with trade monitoring"""
        self.running = True
        self.last_hourly_update = datetime.now()
        self.last_trade_check = datetime.now()
        
        scan_interval = 300  # 5 minutes
        trade_check_interval = self.config.CHECK_TRADES_INTERVAL  # 30 seconds
        hourly_interval = 3600
        
        logger.info("Starting main trading loop")
        print(Fore.YELLOW + "[LOOP] Entering main trading loop")
        print(Fore.CYAN + f"  • Market scan: every {scan_interval//60} minutes")
        print(Fore.CYAN + f"  • Trade check: every {trade_check_interval} seconds")
        print(Fore.CYAN + f"  • Market updates: every hour")
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Market scan every 5 minutes
                await self.scan_markets()
                
                # Check active trades every 30 seconds
                time_since_check = (datetime.now() - self.last_trade_check).total_seconds()
                if time_since_check >= trade_check_interval:
                    await self.monitor_trades()
                    self.last_trade_check = datetime.now()
                
                # Hourly update check
                time_since_update = (datetime.now() - self.last_hourly_update).total_seconds()
                if time_since_update >= hourly_interval:
                    await self.send_hourly_update()
                    self.last_hourly_update = datetime.now()
                
                # Sleep for remaining time
                elapsed = time.time() - loop_start
                sleep_time = max(0, min(scan_interval, trade_check_interval) - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            print(Fore.YELLOW + "\n[SYSTEM] Shutdown signal received")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            print(Fore.RED + f"[ERROR] Main loop error: {e}")
        finally:
            await self.shutdown()
    
    async def scan_markets(self):
        """Scan all markets for trading opportunities"""
        try:
            print(Fore.CYAN + f"[SCAN] Market scan started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            symbols = self.config.TRADING_SYMBOLS
            
            for symbol in symbols:
                try:
                    # Analyze market
                    market_state = await self.market_analyzer.analyze(symbol)
                    
                    if not market_state:
                        continue
                    
                    # Generate signal (with duplicate prevention)
                    signal = await self.signal_generator.generate_signal(symbol, market_state)
                    
                    if signal:
                        # Broadcast signal to Telegram
                        await self.telegram_handler.broadcast_signal(signal)
                        
                        # Store signal for ML training
                        await self.ml_engine.store_signal(signal)
                        
                        # Execute on all enabled user accounts
                        execution_results = await self.multi_user_executor.execute_signal_for_all_users(signal)
                        
                        if execution_results:
                            total_executions = sum(len(accs) for accs in execution_results.values())
                            print(Fore.GREEN + f"[EXECUTED] {total_executions} trades across {len(execution_results)} users")
                            
                            # Send execution confirmations
                            await self.telegram_handler.send_execution_confirmations(signal, execution_results)
                        
                        logger.info(f"Signal generated for {symbol}: {signal['direction']} {signal['entry_type']}")
                        print(Fore.GREEN + f"[SIGNAL] {symbol} {signal['direction']} {signal['entry_type']} @ {signal['entry_price']:.5f}")
                        
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")
            
            # Display active signals count
            active_count = self.signal_generator.get_active_signals_count()
            print(Fore.CYAN + f"[SCAN] Completed | Active signals: {active_count}")
            
        except Exception as e:
            logger.error(f"Error in market scan: {e}", exc_info=True)
    
    async def monitor_trades(self):
        """Monitor active trades for TP/SL hits"""
        try:
            # Check for TP/SL hits
            notifications = await self.signal_generator.check_active_signals()
            
            # Send notifications for closed trades
            for notification in notifications:
                await self.telegram_handler.send_trade_closed_notification(notification)
                logger.info(f"Trade closed: {notification['symbol']} {notification['outcome']} {notification['pips']:.1f} pips")
            
        except Exception as e:
            logger.error(f"Error monitoring trades: {e}", exc_info=True)
    
    async def send_hourly_update(self):
        """Send hourly market update"""
        try:
            print(Fore.MAGENTA + "[UPDATE] Generating hourly market update...")
            
            updates = []
            
            for symbol in self.config.TRADING_SYMBOLS:
                try:
                    market_state = await self.market_analyzer.analyze(symbol)
                    if market_state:
                        update = self._format_market_update(symbol, market_state)
                        updates.append(update)
                except Exception as e:
                    logger.error(f"Error getting update for {symbol}: {e}")
            
            if updates:
                # Include win rate stats
                win_rate_stats = self.signal_generator.get_win_rate()
                message = self._format_hourly_message(updates, win_rate_stats)
                await self.telegram_handler.broadcast_message(message)
                print(Fore.GREEN + "[UPDATE] Hourly update sent")
            
        except Exception as e:
            logger.error(f"Error sending hourly update: {e}", exc_info=True)
    
    def _format_startup_message(self):
        """Format bot startup notification"""
        account_stats = self.account_manager.get_total_accounts()
        
        return f"""
<b>NIXIE'S TRADING BOT - SYSTEM ONLINE</b>

<b>Status:</b> Active
<b>Started:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
<b>Author:</b> Blessing Omoregie

<b>Configuration:</b>
- Symbols: {len(self.config.TRADING_SYMBOLS)} pairs
- Scan Interval: 5 minutes
- Trade Monitoring: 30 seconds
- Update Interval: 1 hour
- ML Engine: Enabled
- Strategy: SMC Institutional Precision

<b>Multi-User System:</b>
- Users with accounts: {account_stats['total_users']}
- Total accounts: {account_stats['total_accounts']}
- Active accounts: {account_stats['enabled_accounts']}

<b>NEW FEATURES:</b>
✓ Duplicate signal prevention
✓ Auto CSV export
✓ TP/SL monitoring & notifications
✓ Multi-user MT5 auto-execution
✓ Secure account management
✓ Accurate win rate tracking

<b>System Message:</b>
All trading systems operational. Multi-user execution ready.
"""
    
    def _format_market_update(self, symbol, market_state):
        """Format individual market update"""
        return {
            'symbol': symbol,
            'price': market_state.get('current_price', 0),
            'trend': market_state.get('htf_trend', 'NEUTRAL'),
            'volatility': market_state.get('volatility', 'MEDIUM'),
            'bias': market_state.get('bias', 'NEUTRAL')
        }
    
    def _format_hourly_message(self, updates, win_rate_stats):
        """Format hourly update message with stats"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        message = f"<b>HOURLY MARKET UPDATE</b>\n"
        message += f"<b>Time:</b> {timestamp}\n\n"
        
        # Performance stats
        message += f"<b>📊 Bot Performance:</b>\n"
        message += f"Win Rate: {win_rate_stats['win_rate']:.1f}%\n"
        message += f"Trades: {win_rate_stats['wins']}W / {win_rate_stats['losses']}L\n"
        message += f"Active Signals: {self.signal_generator.get_active_signals_count()}\n\n"
        
        # Market conditions
        message += f"<b>💹 Market Conditions:</b>\n"
        for update in updates[:10]:  # Show first 10
            message += f"<b>{update['symbol']}</b> - {update['price']:.5f}\n"
            message += f"  {update['trend']} | {update['volatility']} vol | {update['bias']}\n"
        
        if len(updates) > 10:
            message += f"\n<i>...and {len(updates)-10} more pairs</i>\n"
        
        message += "\n<i>Monitoring markets continuously...</i>"
        
        return message
    
    async def shutdown(self):
        """Gracefully shutdown the bot"""
        try:
            print(Fore.YELLOW + "\n[SYSTEM] Initiating graceful shutdown...")
            
            # Send shutdown notification
            if self.telegram_handler:
                try:
                    win_rate_stats = self.signal_generator.get_win_rate()
                    shutdown_msg = f"""
<b>NIXIE'S TRADING BOT - SYSTEM OFFLINE</b>

<b>Status:</b> Stopped
<b>Stopped:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

<b>Final Stats:</b>
- Win Rate: {win_rate_stats['win_rate']:.1f}%
- Total Trades: {win_rate_stats['total']}
- Wins: {win_rate_stats['wins']}
- Losses: {win_rate_stats['losses']}

All data saved to CSV files.
The bot has been shut down gracefully.
"""
                    await self.telegram_handler.broadcast_message(shutdown_msg)
                except Exception as e:
                    logger.error(f"Failed to send shutdown notification: {e}")
                
                await self.telegram_handler.shutdown()
            
            # Disconnect MT5
            if self.mt5_connection:
                await self.mt5_connection.disconnect()
            
            # Save ML model
            if self.ml_engine:
                await self.ml_engine.save_model()
            
            logger.info("Bot shutdown completed")
            print(Fore.GREEN + "[SYSTEM] Shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main():
    """Main entry point"""
    bot = NixieTradingBot()
    
    bot.display_banner()
    
    if await bot.initialize():
        await bot.run()
    else:
        print(Fore.RED + "[SYSTEM] Failed to start bot. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n[SYSTEM] Bot stopped by user")
    except Exception as e:
        print(Fore.RED + f"[FATAL] Unexpected error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
        
    def display_banner(self):
        """Display animated startup banner"""
        banner_text = "NIXIE'S TRADING BOT"
        fig = Figlet(font='slant')
        ascii_banner = fig.renderText(banner_text)
        
        colors = [Fore.CYAN, Fore.BLUE, Fore.MAGENTA, Fore.CYAN]
        
        for color in colors:
            sys.stdout.write('\033[2J\033[H')
            print(color + Style.BRIGHT + ascii_banner)
            print(Fore.WHITE + Style.BRIGHT + "=" * 80)
            print(Fore.GREEN + Style.BRIGHT + "High-Precision Institutional Scalping System")
            print(Fore.YELLOW + "Author: Blessing Omoregie (Nixiestone)")
            print(Fore.WHITE + "=" * 80)
            time.sleep(0.3)
        
        print(Fore.GREEN + "\n[SYSTEM] Initializing trading systems...")
        time.sleep(1)
    
    async def initialize(self):
        """Initialize all bot components"""
        try:
            logger.info("Starting Nixie's Trading Bot initialization...")
            
            # Validate configuration
            print(Fore.CYAN + "[CONFIG] Validating configuration...")
            try:
                self.config.validate()
                print(Fore.GREEN + "[CONFIG] Configuration valid")
            except ValueError as e:
                print(Fore.RED + f"[ERROR] Configuration invalid: {e}")
                return False
            
            # Initialize MT5 connection
            print(Fore.CYAN + "[MT5] Connecting to MetaTrader 5...")
            self.mt5_connection = MT5Connection(self.config)
            if not await self.mt5_connection.connect():
                print(Fore.RED + "[ERROR] Failed to connect to MT5")
                return False
            print(Fore.GREEN + "[MT5] Connected successfully")
            
            # Initialize auto-executor
            print(Fore.CYAN + "[EXECUTOR] Initializing auto-execution module...")
            self.auto_executor = MT5AutoExecutor(self.mt5_connection, self.config)
            
            # Check config for auto-execution
            if self.config.AUTO_EXECUTE_TRADES:
                self.auto_executor.enable()
                print(Fore.YELLOW + "[EXECUTOR] ⚠️  AUTO-EXECUTION ENABLED - Trades will be executed automatically!")
            else:
                print(Fore.GREEN + "[EXECUTOR] Auto-execution disabled (signals only)")
            
            # Initialize market analyzer
            print(Fore.CYAN + "[ANALYZER] Initializing market analysis engine...")
            self.market_analyzer = MarketAnalyzer(self.mt5_connection, self.config)
            print(Fore.GREEN + "[ANALYZER] Market analyzer ready")
            
            # Initialize ML engine
            print(Fore.CYAN + "[ML] Loading machine learning engine...")
            self.ml_engine = MLEngine(self.config)
            await self.ml_engine.initialize()
            print(Fore.GREEN + "[ML] Machine learning engine loaded")
            
            # Initialize signal generator (ENHANCED VERSION)
            print(Fore.CYAN + "[SIGNAL] Initializing enhanced signal generation system...")
            self.signal_generator = SignalGenerator(
                self.market_analyzer,
                self.ml_engine,
                self.config
            )
            print(Fore.GREEN + "[SIGNAL] Signal generator ready with:")
            print(Fore.GREEN + "  ✓ Duplicate prevention")
            print(Fore.GREEN + "  ✓ Auto CSV export")
            print(Fore.GREEN + "  ✓ Trade monitoring")
            print(Fore.GREEN + "  ✓ Win rate tracking")
            
            # Initialize Telegram handler
            print(Fore.CYAN + "[TELEGRAM] Starting Telegram bot...")
            self.telegram_handler = TelegramBotHandler(self.config, self)
            
            try:
                await self.telegram_handler.initialize()
                print(Fore.GREEN + "[TELEGRAM] Telegram bot started")
            except Exception as e:
                print(Fore.RED + f"[ERROR] Telegram initialization failed: {e}")
                return False
            
            # Send startup notification
            try:
                await self.telegram_handler.broadcast_message(
                    self._format_startup_message()
                )
                print(Fore.GREEN + "[TELEGRAM] Startup notification sent")
            except Exception as e:
                logger.error(f"Failed to send startup notification: {e}")
            
            logger.info("Bot initialization completed successfully")
            print(Fore.GREEN + Style.BRIGHT + "\n[SYSTEM] All systems operational. Bot is now active.\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            print(Fore.RED + f"[ERROR] Initialization failed: {e}")
            return False
    
    async def run(self):
        """Main bot loop with trade monitoring"""
        self.running = True
        self.last_hourly_update = datetime.now()
        self.last_trade_check = datetime.now()
        
        scan_interval = 300  # 5 minutes
        trade_check_interval = self.config.CHECK_TRADES_INTERVAL  # 30 seconds
        hourly_interval = 3600
        
        logger.info("Starting main trading loop")
        print(Fore.YELLOW + "[LOOP] Entering main trading loop")
        print(Fore.CYAN + f"  • Market scan: every {scan_interval//60} minutes")
        print(Fore.CYAN + f"  • Trade check: every {trade_check_interval} seconds")
        print(Fore.CYAN + f"  • Market updates: every hour")
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Market scan every 5 minutes
                await self.scan_markets()
                
                # Check active trades every 30 seconds
                time_since_check = (datetime.now() - self.last_trade_check).total_seconds()
                if time_since_check >= trade_check_interval:
                    await self.monitor_trades()
                    self.last_trade_check = datetime.now()
                
                # Hourly update check
                time_since_update = (datetime.now() - self.last_hourly_update).total_seconds()
                if time_since_update >= hourly_interval:
                    await self.send_hourly_update()
                    self.last_hourly_update = datetime.now()
                
                # Sleep for remaining time
                elapsed = time.time() - loop_start
                sleep_time = max(0, min(scan_interval, trade_check_interval) - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            print(Fore.YELLOW + "\n[SYSTEM] Shutdown signal received")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            print(Fore.RED + f"[ERROR] Main loop error: {e}")
        finally:
            await self.shutdown()
    
    async def scan_markets(self):
        """Scan all markets for trading opportunities"""
        try:
            print(Fore.CYAN + f"[SCAN] Market scan started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            symbols = self.config.TRADING_SYMBOLS
            
            for symbol in symbols:
                try:
                    # Analyze market
                    market_state = await self.market_analyzer.analyze(symbol)
                    
                    if not market_state:
                        continue
                    
                    # Generate signal (with duplicate prevention)
                    signal = await self.signal_generator.generate_signal(symbol, market_state)
                    
                    if signal:
                        # Broadcast signal to Telegram
                        await self.telegram_handler.broadcast_signal(signal)
                        
                        # Store signal for ML training
                        await self.ml_engine.store_signal(signal)
                        
                        # Execute in MT5 if enabled
                        if self.auto_executor.is_enabled():
                            ticket = await self.auto_executor.execute_signal(signal)
                            if ticket:
                                signal['mt5_ticket'] = ticket
                                print(Fore.GREEN + f"[EXECUTED] Trade opened in MT5 - Ticket: {ticket}")
                        
                        logger.info(f"Signal generated for {symbol}: {signal['direction']} {signal['entry_type']}")
                        print(Fore.GREEN + f"[SIGNAL] {symbol} {signal['direction']} {signal['entry_type']} @ {signal['entry_price']:.5f}")
                        
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")
            
            # Display active signals count
            active_count = self.signal_generator.get_active_signals_count()
            print(Fore.CYAN + f"[SCAN] Completed | Active signals: {active_count}")
            
        except Exception as e:
            logger.error(f"Error in market scan: {e}", exc_info=True)
    
    async def monitor_trades(self):
        """Monitor active trades for TP/SL hits"""
        try:
            # Check for TP/SL hits
            notifications = await self.signal_generator.check_active_signals()
            
            # Send notifications for closed trades
            for notification in notifications:
                await self.telegram_handler.send_trade_closed_notification(notification)
                
                # Close MT5 position if auto-execution is enabled
                if self.auto_executor.is_enabled():
                    await self.auto_executor.close_position(notification['signal_id'])
                
                logger.info(f"Trade closed: {notification['symbol']} {notification['outcome']} {notification['pips']:.1f} pips")
            
        except Exception as e:
            logger.error(f"Error monitoring trades: {e}", exc_info=True)
    
    async def send_hourly_update(self):
        """Send hourly market update"""
        try:
            print(Fore.MAGENTA + "[UPDATE] Generating hourly market update...")
            
            updates = []
            
            for symbol in self.config.TRADING_SYMBOLS:
                try:
                    market_state = await self.market_analyzer.analyze(symbol)
                    if market_state:
                        update = self._format_market_update(symbol, market_state)
                        updates.append(update)
                except Exception as e:
                    logger.error(f"Error getting update for {symbol}: {e}")
            
            if updates:
                # Include win rate stats
                win_rate_stats = self.signal_generator.get_win_rate()
                message = self._format_hourly_message(updates, win_rate_stats)
                await self.telegram_handler.broadcast_message(message)
                print(Fore.GREEN + "[UPDATE] Hourly update sent")
            
        except Exception as e:
            logger.error(f"Error sending hourly update: {e}", exc_info=True)
    
    def _format_startup_message(self):
        """Format bot startup notification"""
        auto_exec_status = "ENABLED ⚠️" if self.auto_executor.is_enabled() else "DISABLED ✓"
        
        return f"""
<b>NIXIE'S TRADING BOT - SYSTEM ONLINE</b>

<b>Status:</b> Active
<b>Started:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
<b>Author:</b> Blessing Omoregie

<b>Configuration:</b>
- Symbols: {len(self.config.TRADING_SYMBOLS)} pairs
- Scan Interval: 5 minutes
- Trade Monitoring: 30 seconds
- Update Interval: 1 hour
- ML Engine: Enabled
- Strategy: SMC Institutional Precision

<b>NEW FEATURES:</b>
✓ Duplicate signal prevention
✓ Auto CSV export
✓ TP/SL monitoring & notifications
✓ MT5 Auto-Execution: {auto_exec_status}
✓ Accurate win rate tracking

<b>System Message:</b>
All trading systems operational. Enhanced trade management active.
"""
    
    def _format_market_update(self, symbol, market_state):
        """Format individual market update"""
        return {
            'symbol': symbol,
            'price': market_state.get('current_price', 0),
            'trend': market_state.get('htf_trend', 'NEUTRAL'),
            'volatility': market_state.get('volatility', 'MEDIUM'),
            'bias': market_state.get('bias', 'NEUTRAL')
        }
    
    def _format_hourly_message(self, updates, win_rate_stats):
        """Format hourly update message with stats"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        message = f"<b>HOURLY MARKET UPDATE</b>\n"
        message += f"<b>Time:</b> {timestamp}\n\n"
        
        # Performance stats
        message += f"<b>📊 Bot Performance:</b>\n"
        message += f"Win Rate: {win_rate_stats['win_rate']:.1f}%\n"
        message += f"Trades: {win_rate_stats['wins']}W / {win_rate_stats['losses']}L\n"
        message += f"Active Signals: {self.signal_generator.get_active_signals_count()}\n\n"
        
        # Market conditions
        message += f"<b>💹 Market Conditions:</b>\n"
        for update in updates[:10]:  # Show first 10
            message += f"<b>{update['symbol']}</b> - {update['price']:.5f}\n"
            message += f"  {update['trend']} | {update['volatility']} vol | {update['bias']}\n"
        
        if len(updates) > 10:
            message += f"\n<i>...and {len(updates)-10} more pairs</i>\n"
        
        message += "\n<i>Monitoring markets continuously...</i>"
        
        return message
    
    async def shutdown(self):
        """Gracefully shutdown the bot"""
        try:
            print(Fore.YELLOW + "\n[SYSTEM] Initiating graceful shutdown...")
            
            # Send shutdown notification
            if self.telegram_handler:
                try:
                    win_rate_stats = self.signal_generator.get_win_rate()
                    shutdown_msg = f"""
<b>NIXIE'S TRADING BOT - SYSTEM OFFLINE</b>

<b>Status:</b> Stopped
<b>Stopped:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

<b>Final Stats:</b>
- Win Rate: {win_rate_stats['win_rate']:.1f}%
- Total Trades: {win_rate_stats['total']}
- Wins: {win_rate_stats['wins']}
- Losses: {win_rate_stats['losses']}

All data saved to CSV files.
The bot has been shut down gracefully.
"""
                    await self.telegram_handler.broadcast_message(shutdown_msg)
                except Exception as e:
                    logger.error(f"Failed to send shutdown notification: {e}")
                
                await self.telegram_handler.shutdown()
            
            # Disconnect MT5
            if self.mt5_connection:
                await self.mt5_connection.disconnect()
            
            # Save ML model
            if self.ml_engine:
                await self.ml_engine.save_model()
            
            logger.info("Bot shutdown completed")
            print(Fore.GREEN + "[SYSTEM] Shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main():
    """Main entry point"""
    bot = NixieTradingBot()
    
    bot.display_banner()
    
    if await bot.initialize():
        await bot.run()
    else:
        print(Fore.RED + "[SYSTEM] Failed to start bot. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n[SYSTEM] Bot stopped by user")
    except Exception as e:
        print(Fore.RED + f"[FATAL] Unexpected error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)