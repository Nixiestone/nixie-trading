"""
Enhanced Telegram Bot Handler
NOW WITH: TP/SL hit notifications with detailed analysis
"""

import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from datetime import datetime
from typing import Dict, List
from src.utils.logger import setup_logger
from src.utils.database import Database

logger = setup_logger(__name__)


class TelegramBotHandler:
    """Enhanced Telegram bot with trade notifications"""
    
    def __init__(self, config, main_bot):
        self.config = config
        self.main_bot = main_bot
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.app = None
        self.bot = None
        self.db = Database(config.DB_PATH)
        
    async def initialize(self):
        """Initialize Telegram bot"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Initializing Telegram bot (attempt {attempt}/{max_retries})...")
                
                request = HTTPXRequest(
                    connection_pool_size=8,
                    connect_timeout=30.0,
                    read_timeout=30.0,
                    write_timeout=30.0,
                    pool_timeout=30.0
                )
                
                self.app = Application.builder().token(self.bot_token).request(request).build()
                self.bot = self.app.bot
                
                # Add command handlers
                self.app.add_handler(CommandHandler("start", self.cmd_start))
                self.app.add_handler(CommandHandler("subscribe", self.cmd_subscribe))
                self.app.add_handler(CommandHandler("unsubscribe", self.cmd_unsubscribe))
                self.app.add_handler(CommandHandler("status", self.cmd_status))
                self.app.add_handler(CommandHandler("stats", self.cmd_stats))
                self.app.add_handler(CommandHandler("help", self.cmd_help))
                self.app.add_handler(CommandHandler("autoexec", self.cmd_autoexec))  # NEW
                
                await asyncio.wait_for(self.app.initialize(), timeout=30)
                await asyncio.wait_for(self.app.start(), timeout=30)
                await asyncio.wait_for(self.app.updater.start_polling(drop_pending_updates=True), timeout=30)
                
                logger.info("Telegram bot started successfully")
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"Telegram timeout on attempt {attempt}/{max_retries}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                else:
                    raise Exception("Telegram API connection timeout")
            except Exception as e:
                logger.error(f"Telegram init error on attempt {attempt}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                else:
                    raise
    
    async def shutdown(self):
        """Shutdown Telegram bot"""
        try:
            if self.app:
                await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
            logger.info("Telegram bot shut down")
        except Exception as e:
            logger.error(f"Error shutting down Telegram: {e}")
    
    async def cmd_autoexec(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /autoexec command - toggle auto-execution"""
        try:
            user_id = update.effective_user.id
            
            # Only admin can control auto-execution
            if str(user_id) != self.config.TELEGRAM_ADMIN_ID:
                await update.message.reply_text(
                    "⛔ Admin access required for this command.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Check if there are arguments
            if context.args:
                command = context.args[0].lower()
                
                if command == 'on':
                    self.main_bot.auto_executor.enable()
                    message = """
<b>⚠️ AUTO-EXECUTION ENABLED</b>

The bot will now automatically execute ALL signals in MetaTrader 5.

<b>This means:</b>
✓ Signals will be placed as real orders
✓ Stop Loss and Take Profit will be set
✓ Risk management will be applied (2% per trade)
✓ You will receive notifications

<b>⚠️ WARNING:</b>
Make sure you are ready to trade real money!

Use <code>/autoexec off</code> to disable.
"""
                    await update.message.reply_text(message, parse_mode=ParseMode.HTML)
                    logger.info(f"Admin {user_id} ENABLED auto-execution")
                    
                elif command == 'off':
                    self.main_bot.auto_executor.disable()
                    message = """
<b>✓ AUTO-EXECUTION DISABLED</b>

The bot will now ONLY send signal notifications.
Trades will NOT be executed automatically.

You can manually place trades based on signals received.

Use <code>/autoexec on</code> to re-enable.
"""
                    await update.message.reply_text(message, parse_mode=ParseMode.HTML)
                    logger.info(f"Admin {user_id} DISABLED auto-execution")
                    
                else:
                    await update.message.reply_text(
                        "Usage: /autoexec on | /autoexec off",
                        parse_mode=ParseMode.HTML
                    )
            else:
                # Show current status
                status = "ENABLED ⚠️" if self.main_bot.auto_executor.is_enabled() else "DISABLED ✓"
                active_positions = self.main_bot.auto_executor.get_active_positions_count()
                
                message = f"""
<b>AUTO-EXECUTION STATUS</b>

<b>Status:</b> {status}
<b>Active Positions:</b> {active_positions}

<b>Commands:</b>
<code>/autoexec on</code> - Enable auto-execution
<code>/autoexec off</code> - Disable auto-execution

<b>⚠️ Note:</b> Only signals generated AFTER enabling will be auto-executed.
"""
                await update.message.reply_text(message, parse_mode=ParseMode.HTML)
                
        except Exception as e:
            logger.error(f"Error in autoexec command: {e}")
            await update.message.reply_text("An error occurred.")
    
    async def send_trade_closed_notification(self, notification: Dict):
        """Send notification when TP or SL hits"""
        try:
            # Format the notification message
            message = self._format_trade_closed_message(notification)
            
            # Send to all subscribers
            subscribers = await self.db.get_subscribers()
            
            for subscriber in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=subscriber['user_id'],
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send notification to {subscriber['user_id']}: {e}")
            
            logger.info(f"Trade closed notification sent: {notification['symbol']} {notification['outcome']}")
            
        except Exception as e:
            logger.error(f"Error sending trade closed notification: {e}", exc_info=True)
    
    def _format_trade_closed_message(self, notification: Dict) -> str:
        """Format trade closed notification"""
        outcome = notification['outcome']
        symbol = notification['symbol']
        direction = notification['direction']
        pips = notification['pips']
        duration = notification['duration']
        reason = notification['reason']
        entry_price = notification['entry_price']
        exit_price = notification['exit_price']
        setup_type = notification['setup_type']
        
        # Emoji based on outcome
        emoji = "🎉" if outcome == 'WIN' else "⚠️"
        outcome_text = "TAKE PROFIT HIT" if outcome == 'WIN' else "STOP LOSS HIT"
        color_indicator = "🟢" if outcome == 'WIN' else "🔴"
        
        message = f"""
<b>{emoji} TRADE CLOSED - {outcome_text}</b>

{color_indicator} <b>Symbol:</b> {symbol}
<b>Direction:</b> {direction}
<b>Outcome:</b> {outcome}

<b>📊 TRADE DETAILS:</b>
<b>Entry Price:</b> {entry_price:.5f}
<b>Exit Price:</b> {exit_price:.5f}
<b>Pips Result:</b> {'+' if pips > 0 else ''}{pips:.1f} pips
<b>Duration:</b> {duration}
<b>Setup Type:</b> {setup_type}

<b>📝 ANALYSIS:</b>
{reason}

<b>⏰ Time Closed:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        if outcome == 'WIN':
            message += "\n<i>Great trade! Keep following the strategy! 🚀</i>"
        else:
            message += "\n<i>Stop loss protected your capital. On to the next setup! 💪</i>"
        
        return message
    
    # Keep all previous command handlers...
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "Trader"
            
            welcome_message = f"""
<b>👋 Hello {first_name}, Welcome to NIXIE'S TRADING BOT!</b>

🎯 <b>Enhanced Features:</b>
✓ High-precision SMC signals
✓ Duplicate prevention
✓ Auto CSV export
✓ TP/SL hit notifications
✓ MT5 auto-execution (optional)
✓ Accurate win rate tracking

<b>📱 Commands:</b>
/subscribe - Start receiving signals
/unsubscribe - Stop receiving signals
/status - Check your status
/stats - View performance stats
/autoexec - Control auto-execution (Admin)
/help - Get detailed help

<i>Built with precision by Blessing Omoregie</i>
"""
            
            await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
    
    async def cmd_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or "Unknown"
            
            is_subscribed = await self.db.is_user_subscribed(user_id)
            
            if is_subscribed:
                await update.message.reply_text(
                    "You are already subscribed to trading signals.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            await self.db.subscribe_user(user_id, username)
            
            message = """
<b>✅ SUBSCRIPTION ACTIVATED</b>

You will now receive:
✓ High-probability trading signals
✓ TP/SL hit notifications
✓ Hourly market updates
✓ Performance tracking

<i>Stay disciplined and follow risk management!</i>
"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            logger.info(f"User {user_id} subscribed")
            
        except Exception as e:
            logger.error(f"Error in subscribe command: {e}")
    
    async def cmd_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unsubscribe command"""
        try:
            user_id = update.effective_user.id
            
            is_subscribed = await self.db.is_user_subscribed(user_id)
            
            if not is_subscribed:
                await update.message.reply_text("You are not subscribed.")
                return
            
            await self.db.unsubscribe_user(user_id)
            
            await update.message.reply_text(
                "<b>SUBSCRIPTION CANCELLED</b>\n\nYou will no longer receive signals.",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"User {user_id} unsubscribed")
            
        except Exception as e:
            logger.error(f"Error in unsubscribe command: {e}")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "Trader"
            
            is_subscribed = await self.db.is_user_subscribed(user_id)
            
            status_emoji = "✅" if is_subscribed else "❌"
            status_text = "ACTIVE" if is_subscribed else "INACTIVE"
            
            message = f"""
<b>📊 SUBSCRIPTION STATUS</b>

<b>Hello {first_name}!</b>

<b>Status:</b> {status_emoji} {status_text}
<b>User ID:</b> {user_id}
"""
            
            if is_subscribed:
                message += """
<b>✓ You are receiving:</b>
• Trading signals
• TP/SL notifications
• Market updates
• Performance stats
"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            # Get win rate from signal generator
            win_rate_stats = self.main_bot.signal_generator.get_win_rate()
            active_signals = self.main_bot.signal_generator.get_active_signals_count()
            ml_stats = await self.main_bot.ml_engine.get_model_stats()
            subscribers = await self.db.get_subscriber_count()
            auto_exec_status = "ENABLED ⚠️" if self.main_bot.auto_executor.is_enabled() else "DISABLED"
            
            message = f"""
<b>📊 BOT STATISTICS</b>

<b>Performance:</b>
- Win Rate: {win_rate_stats['win_rate']:.1f}%
- Total Trades: {win_rate_stats['total']}
- Wins: {win_rate_stats['wins']} | Losses: {win_rate_stats['losses']}
- Profit Factor: {win_rate_stats['profit_factor']:.2f}

<b>Active:</b>
- Monitoring: {active_signals} signals
- Subscribers: {subscribers}

<b>ML Engine:</b>
- Model Trained: {'Yes' if ml_stats.get('model_trained') else 'No'}
- Training Data: {ml_stats.get('total_signals', 0)} signals

<b>Auto-Execution:</b> {auto_exec_status}

<i>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        first_name = update.effective_user.first_name or "Trader"
        
        help_message = f"""
<b>📚 HELP GUIDE</b>

<b>Commands:</b>
/start - Welcome & overview
/subscribe - Get signals
/unsubscribe - Stop signals
/status - Check subscription
/stats - Performance stats
/autoexec - Control auto-execution (Admin)
/help - This message

<b>Signal Notifications:</b>
You will receive notifications for:
✓ New signals generated
✓ Take Profit hits
✓ Stop Loss hits
✓ Hourly market updates

<b>Risk Management:</b>
• Max 2% risk per trade
• Minimum 1:3 R:R ratio
• Follow all signals exactly
• Never overtrade

<i>Trade smart, {first_name}! 🚀</i>
"""
        
        await update.message.reply_text(help_message, parse_mode=ParseMode.HTML)
    
    async def broadcast_signal(self, signal: Dict):
        """Broadcast trading signal"""
        try:
            message = self._format_signal_message(signal)
            subscribers = await self.db.get_subscribers()
            
            for subscriber in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=subscriber['user_id'],
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send to {subscriber['user_id']}: {e}")
            
        except Exception as e:
            logger.error(f"Error broadcasting signal: {e}")
    
    async def broadcast_message(self, message: str):
        """Broadcast general message"""
        try:
            subscribers = await self.db.get_subscribers()
            
            for subscriber in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=subscriber['user_id'],
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send to {subscriber['user_id']}: {e}")
            
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
    
    def _format_signal_message(self, signal: Dict) -> str:
        """Format signal message"""
        timestamp = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')
        direction_emoji = "🔼" if signal['direction'] == 'BUY' else "🔽"
        
        message = f"""
<b>🚨 NEW TRADING SIGNAL</b>

{direction_emoji} <b>Symbol:</b> {signal['symbol']}
<b>Direction:</b> {signal['direction']}
<b>Entry Type:</b> {signal['entry_type']}
<b>Signal Strength:</b> {signal['signal_strength']}

<b>📍 ENTRY:</b>
Entry Price: {signal['entry_price']:.5f}

<b>🎯 TARGETS:</b>
Stop Loss: {signal['stop_loss']:.5f} ({signal['sl_pips']:.1f} pips)
Take Profit: {signal['take_profit']:.5f} ({signal['tp_pips']:.1f} pips)
Risk:Reward: 1:{signal['risk_reward']:.2f}

<b>📊 TECHNICAL:</b>
Setup: {signal['setup_type']}
ML Confidence: {signal['ml_confidence']:.1f}%
Current Price: {signal['current_price']:.5f}
Trend: {signal['trend']}
Volatility: {signal['volatility']}

<b>Signal ID:</b> {signal['signal_id']}
<b>Time:</b> {timestamp}

<i>Max 2% risk. Follow strict risk management!</i>
"""
        
        return message