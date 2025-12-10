"""
Enhanced Telegram Bot Handler with User Account Management
FIXED VERSION - All methods complete, proper error handling
"""

import os
import asyncio
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from telegram.error import TimedOut, NetworkError, RetryAfter
from datetime import datetime
from typing import Dict, List
from src.utils.logger import setup_logger
from src.utils.database import Database
from src.telegram.pdf_generator import PDFGenerator

logger = setup_logger(__name__)


class TelegramBotHandler:
    """Enhanced Telegram bot with user account management"""
    
    def __init__(self, config, main_bot):
        self.config = config
        self.main_bot = main_bot
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.app = None
        self.bot = None
        self.db = Database(config.DB_PATH)
        self.pdf_generator = PDFGenerator()
        
    async def initialize(self):
        """Initialize Telegram bot"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Initializing Telegram bot (attempt {attempt}/{max_retries})...")
                
                # Increased timeouts for better reliability
                request = HTTPXRequest(
                    connection_pool_size=8,
                    connect_timeout=60.0,
                    read_timeout=60.0,
                    write_timeout=60.0,
                    pool_timeout=60.0
                )
                
                self.app = Application.builder().token(self.bot_token).request(request).build()
                self.bot = self.app.bot
                
                # Basic commands
                self.app.add_handler(CommandHandler("start", self.cmd_start))
                self.app.add_handler(CommandHandler("subscribe", self.cmd_subscribe))
                self.app.add_handler(CommandHandler("unsubscribe", self.cmd_unsubscribe))
                self.app.add_handler(CommandHandler("status", self.cmd_status))
                self.app.add_handler(CommandHandler("stats", self.cmd_stats))
                self.app.add_handler(CommandHandler("help", self.cmd_help))
                
                # Admin commands
                self.app.add_handler(CommandHandler("downloadsignals", self.cmd_download_signals))
                self.app.add_handler(CommandHandler("downloadclosed", self.cmd_download_closed))
                
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
    
    # ==================== BASIC COMMANDS ====================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "Trader"
            
            welcome_message = f"""
<b>👋 Hello {first_name}, Welcome to NIXIE'S TRADING BOT!</b>

🎯 <b>Features:</b>
✓ High-precision SMC signals
✓ TP/SL hit notifications
✓ Accurate win rate tracking
✓ MT5 auto-execution (optional)

<b>📱 Commands:</b>
/subscribe - Get trading signals
/unsubscribe - Stop signals
/status - Check subscription
/stats - View performance
/help - Detailed help

<b>🔐 Security:</b>
All signals are based on institutional SMC strategy.
Risk management built-in (2% max per trade).

<i>Built by Blessing Omoregie (Nixiestone)</i>
"""
            
            await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
    
    async def cmd_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            
            # Check if already subscribed
            is_subscribed = await self.db.is_user_subscribed(user_id)
            
            if is_subscribed:
                await update.message.reply_text(
                    "✅ You are already subscribed to trading signals!",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Subscribe user
            await self.db.subscribe_user(user_id, username)
            
            message = f"""
<b>✅ SUBSCRIPTION ACTIVATED!</b>

You will now receive:
• High-quality SMC trading signals
• TP/SL hit notifications with reasons
• Real-time market updates

<b>What to Expect:</b>
• 2-5 signals per day (quality over quantity)
• Minimum 1:3 Risk:Reward ratio
• 65%+ target win rate
• Detailed entry analysis

<b>Risk Management:</b>
• Never risk more than 2% per trade
• Always use suggested stop losses
• Follow the signals exactly as given

<i>Happy trading! 🚀</i>
"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            logger.info(f"User {user_id} ({username}) subscribed")
            
        except Exception as e:
            logger.error(f"Error in subscribe command: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
    
    async def cmd_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unsubscribe command"""
        try:
            user_id = update.effective_user.id
            
            # Check if subscribed
            is_subscribed = await self.db.is_user_subscribed(user_id)
            
            if not is_subscribed:
                await update.message.reply_text(
                    "❌ You are not currently subscribed.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Unsubscribe user
            await self.db.unsubscribe_user(user_id)
            
            message = """
<b>✅ UNSUBSCRIBED SUCCESSFULLY</b>

You will no longer receive trading signals.

You can resubscribe anytime with /subscribe

<i>We hope to see you again! 👋</i>
"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            logger.info(f"User {user_id} unsubscribed")
            
        except Exception as e:
            logger.error(f"Error in unsubscribe command: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            user_id = update.effective_user.id
            
            is_subscribed = await self.db.is_user_subscribed(user_id)
            
            if is_subscribed:
                sub_date = await self.db.get_subscription_date(user_id)
                date_str = sub_date.strftime('%Y-%m-%d') if sub_date else 'Unknown'
                
                message = f"""
<b>📊 SUBSCRIPTION STATUS</b>

<b>Status:</b> ✅ ACTIVE
<b>Subscribed Since:</b> {date_str}
<b>Signals:</b> Enabled

You are receiving all trading signals and notifications.

Use /unsubscribe to stop signals.
"""
            else:
                message = """
<b>📊 SUBSCRIPTION STATUS</b>

<b>Status:</b> ❌ INACTIVE
<b>Signals:</b> Disabled

You are not receiving trading signals.

Use /subscribe to start receiving signals.
"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            # Get bot stats
            win_rate_stats = self.main_bot.signal_generator.get_win_rate()
            active_signals = self.main_bot.signal_generator.get_active_signals_count()
            ml_stats = await self.main_bot.ml_engine.get_model_stats()
            subscribers = await self.db.get_subscriber_count()
            
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
- Trained: {'Yes' if ml_stats.get('model_trained') else 'No'}
- Data: {ml_stats.get('total_signals', 0)} signals

<i>Updated: {datetime.now().strftime('%H:%M:%S UTC')}</i>
"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        first_name = update.effective_user.first_name or "Trader"
        
        help_message = f"""
<b>📚 HELP GUIDE</b>

<b>🎯 Basic Commands:</b>
/start - Welcome & overview
/subscribe - Get trading signals
/unsubscribe - Stop signals
/status - Check subscription
/stats - Performance statistics
/help - This message

<b>👑 Admin Commands:</b>
/downloadsignals - Download signals PDF
/downloadclosed - Download closed trades PDF

<b>📊 How It Works:</b>

1. <b>Subscribe:</b>
   • Use /subscribe to start
   • Receive 2-5 quality signals per day
   • Get TP/SL notifications

2. <b>Signals:</b>
   • Based on SMC strategy
   • Minimum 1:3 Risk:Reward
   • Includes entry, SL, TP
   • ML confidence score

3. <b>Risk Management:</b>
   • Never risk more than 2% per trade
   • Always use stop losses
   • Follow signals exactly

<b>🚀 Features:</b>
✓ Duplicate signal prevention
✓ Auto CSV export
✓ TP/SL hit notifications
✓ Accurate win rate tracking

<i>Trade smart, {first_name}! 🚀</i>
"""
        
        await update.message.reply_text(help_message, parse_mode=ParseMode.HTML)
    
    # ==================== ADMIN COMMANDS ====================
    
    async def cmd_download_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Download signals log as PDF (Admin only)"""
        try:
            user_id = str(update.effective_user.id)
            
            # Check if admin
            if user_id != self.config.TELEGRAM_ADMIN_ID:
                await update.message.reply_text(
                    "⛔ This command is only available to the bot administrator.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            await update.message.reply_text("📄 Generating PDF report... Please wait.")
            
            # Check if CSV exists
            if not os.path.exists('data/signals_log.csv'):
                await update.message.reply_text(
                    "❌ No signals data found. Generate some signals first.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Generate PDF
            pdf_file = f"data/signals_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            success = self.pdf_generator.generate_signals_pdf(
                'data/signals_log.csv', 
                pdf_file
            )
            
            if success and os.path.exists(pdf_file):
                # Send PDF
                with open(pdf_file, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=f"Nixie_Signals_{datetime.now().strftime('%Y%m%d')}.pdf",
                        caption="📊 <b>Signals Report</b>\n\nAll generated signals with outcomes.",
                        parse_mode=ParseMode.HTML
                    )
                
                # Clean up
                os.remove(pdf_file)
                logger.info(f"Admin {user_id} downloaded signals PDF")
            else:
                await update.message.reply_text(
                    "❌ Failed to generate PDF. Check logs for details.",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"Error in download signals command: {e}")
            await update.message.reply_text("❌ An error occurred generating the PDF.")

    async def cmd_download_closed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Download closed trades as PDF (Admin only)"""
        try:
            user_id = str(update.effective_user.id)
            
            if user_id != self.config.TELEGRAM_ADMIN_ID:
                await update.message.reply_text(
                    "⛔ This command is only available to the bot administrator.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            await update.message.reply_text("📄 Generating closed trades PDF... Please wait.")
            
            # Check if CSV exists
            if not os.path.exists('data/closed_trades.csv'):
                await update.message.reply_text(
                    "❌ No closed trades data found. Wait for trades to close first.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            pdf_file = f"data/closed_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            success = self.pdf_generator.generate_closed_trades_pdf(
                'data/closed_trades.csv',
                pdf_file
            )
            
            if success and os.path.exists(pdf_file):
                with open(pdf_file, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=f"Nixie_Closed_Trades_{datetime.now().strftime('%Y%m%d')}.pdf",
                        caption="📈 <b>Closed Trades Report</b>\n\nAll completed trades with outcomes.",
                        parse_mode=ParseMode.HTML
                    )
                
                os.remove(pdf_file)
                logger.info(f"Admin {user_id} downloaded closed trades PDF")
            else:
                await update.message.reply_text(
                    "❌ Failed to generate PDF. Check logs for details.",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"Error in download closed command: {e}")
            await update.message.reply_text("❌ An error occurred generating the PDF.")
    
    # ==================== BROADCASTING METHODS ====================
    
    async def broadcast_signal(self, signal: Dict):
        """Broadcast signal to all subscribers"""
        try:
            message = self._format_signal_message(signal)
            await self.broadcast_message(message)
            logger.info(f"Signal broadcast: {signal['symbol']} {signal['direction']}")
            
        except Exception as e:
            logger.error(f"Error broadcasting signal: {e}")
    
    async def broadcast_message(self, message: str):
        """Broadcast message to all subscribers with timeout handling"""
        try:
            subscribers = await self.db.get_subscribers()
            
            if not subscribers:
                logger.warning("No subscribers to broadcast to")
                return
            
            success_count = 0
            fail_count = 0
            
            for subscriber in subscribers:
                try:
                    # Send with timeout and retry logic
                    await asyncio.wait_for(
                        self.bot.send_message(
                            chat_id=subscriber['user_id'],
                            text=message,
                            parse_mode=ParseMode.HTML
                        ),
                        timeout=30.0  # 30 second timeout per message
                    )
                    success_count += 1
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout sending to {subscriber['user_id']}")
                    fail_count += 1
                    
                except TimedOut:
                    logger.warning(f"Telegram timeout for {subscriber['user_id']}")
                    fail_count += 1
                    
                except NetworkError as e:
                    logger.warning(f"Network error for {subscriber['user_id']}: {e}")
                    fail_count += 1
                    
                except RetryAfter as e:
                    logger.warning(f"Rate limited, waiting {e.retry_after}s")
                    await asyncio.sleep(e.retry_after)
                    # Retry once
                    try:
                        await self.bot.send_message(
                            chat_id=subscriber['user_id'],
                            text=message,
                            parse_mode=ParseMode.HTML
                        )
                        success_count += 1
                    except:
                        fail_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to send to {subscriber['user_id']}: {e}")
                    fail_count += 1
            
            logger.info(f"Broadcast complete: {success_count} sent, {fail_count} failed")
            
        except Exception as e:
            logger.error(f"Error in broadcast_message: {e}")
    
    async def send_trade_closed_notification(self, notification: Dict):
        """Send trade closed notification"""
        try:
            message = self._format_trade_closed_message(notification)
            await self.broadcast_message(message)
            logger.info(f"Trade closed notification sent: {notification['symbol']} {notification['outcome']}")
            
        except Exception as e:
            logger.error(f"Error sending trade closed notification: {e}")
    
    # ==================== MESSAGE FORMATTERS ====================
    
    def _format_signal_message(self, signal: Dict) -> str:
        """Format signal for Telegram"""
        return f"""
<b>🚨 NEW TRADING SIGNAL</b>

<b>Symbol:</b> {signal['symbol']}
<b>Direction:</b> {signal['direction']} {self._get_direction_emoji(signal['direction'])}
<b>Signal Strength:</b> {signal['signal_strength']}

<b>📍 ENTRY DETAILS:</b>
Entry Type: {signal['entry_type']}
Entry Price: {signal['entry_price']:.5f}

<b>🛡 RISK MANAGEMENT:</b>
Stop Loss: {signal['stop_loss']:.5f} ({signal['sl_pips']:.1f} pips)
Take Profit: {signal['take_profit']:.5f} ({signal['tp_pips']:.1f} pips)
Risk:Reward: 1:{signal['risk_reward']:.2f}

<b>📊 TECHNICAL DATA:</b>
Setup: {signal['setup_type']}
ML Confidence: {signal['ml_confidence']:.1f}%
Current Price: {signal['current_price']:.5f}
ATR: {signal['atr']:.5f}
RSI: {signal['rsi']:.1f}

<b>📈 MARKET CONDITIONS:</b>
Trend: {signal['trend']}
Bias: {signal['market_bias']}
Volatility: {signal['volatility']}

<b>🕐 Time:</b> {signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}

<i>Signal ID: {signal['signal_id']}</i>
"""
    
    def _format_trade_closed_message(self, notification: Dict) -> str:
        """Format trade closed notification"""
        outcome_emoji = "✅" if notification['outcome'] == 'WIN' else "❌"
        
        return f"""
<b>{outcome_emoji} TRADE CLOSED - {notification['outcome']}</b>

<b>Symbol:</b> {notification['symbol']}
<b>Direction:</b> {notification['direction']}
<b>Outcome:</b> {notification['outcome']}
<b>Pips:</b> {notification['pips']:.1f}
<b>Duration:</b> {notification['duration']}

<b>📊 PRICES:</b>
Entry: {notification['entry_price']:.5f}
Exit: {notification['exit_price']:.5f}

<b>💡 REASON:</b>
{notification['reason']}

<b>Setup:</b> {notification['setup_type']}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

<i>Signal ID: {notification['signal_id']}</i>
"""
    
    def _get_direction_emoji(self, direction: str) -> str:
        """Get emoji for direction"""
        return "🟢" if direction == "BUY" else "🔴"