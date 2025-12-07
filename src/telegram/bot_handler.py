"""
Telegram Bot Handler
Manages user subscriptions and broadcasts signals/updates
FIXED: Added retry logic and better timeout handling
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
    """Handles Telegram bot operations"""
    
    def __init__(self, config, main_bot):
        self.config = config
        self.main_bot = main_bot
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.app = None
        self.bot = None
        self.db = Database(config.DB_PATH)
        
    async def initialize(self):
        """Initialize Telegram bot with retry logic"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Attempting to initialize Telegram bot (attempt {attempt}/{max_retries})...")
                
                # Create custom request with longer timeout
                request = HTTPXRequest(
                    connection_pool_size=8,
                    connect_timeout=30.0,
                    read_timeout=30.0,
                    write_timeout=30.0,
                    pool_timeout=30.0
                )
                
                # Create application with custom request
                self.app = Application.builder().token(self.bot_token).request(request).build()
                self.bot = self.app.bot
                
                # Add command handlers
                self.app.add_handler(CommandHandler("start", self.cmd_start))
                self.app.add_handler(CommandHandler("subscribe", self.cmd_subscribe))
                self.app.add_handler(CommandHandler("unsubscribe", self.cmd_unsubscribe))
                self.app.add_handler(CommandHandler("status", self.cmd_status))
                self.app.add_handler(CommandHandler("stats", self.cmd_stats))
                self.app.add_handler(CommandHandler("help", self.cmd_help))
                
                # Start bot with timeout
                await asyncio.wait_for(self.app.initialize(), timeout=30)
                await asyncio.wait_for(self.app.start(), timeout=30)
                await asyncio.wait_for(self.app.updater.start_polling(drop_pending_updates=True), timeout=30)
                
                logger.info("Telegram bot started successfully")
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"Telegram initialization timeout on attempt {attempt}/{max_retries}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("All Telegram initialization attempts failed")
                    raise Exception("Telegram API connection timeout - check your internet connection or firewall")
                    
            except Exception as e:
                logger.error(f"Error initializing Telegram bot on attempt {attempt}: {e}", exc_info=True)
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
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
            logger.error(f"Error shutting down Telegram bot: {e}")
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "Trader"
            username = update.effective_user.username or "User"
            
            # Log the interaction
            logger.info(f"User {user_id} ({first_name}) sent /start command")
            
            welcome_message = f"""
<b>👋 Hello {first_name}, Welcome to NIXIE'S TRADING BOT!</b>

I'm your AI-powered institutional trading assistant, designed to help you trade like the smart money.

<b>🎯 What I Do:</b>
I analyze Forex pairs, Metals, and Indices using Smart Money Concepts (SMC) to identify high-probability trading opportunities with institutional precision.

<b>💡 Key Features:</b>
• High-precision SMC strategy
• ML-enhanced signal quality (65%+ win rate target)
• Multi-timeframe analysis (H4, H1, M5, M1)
• Minimum 1:3 Risk:Reward ratio
• Real-time market scanning every 5 minutes
• Hourly market updates
• Automatic ML training and improvement

<b>📱 Available Commands:</b>
/subscribe - Start receiving trading signals
/unsubscribe - Stop receiving signals
/status - Check your subscription status
/stats - View bot performance statistics
/help - Get detailed help information

<b>🚀 Ready to Get Started?</b>
Type /subscribe to begin receiving high-quality trading signals!

<b>⚠️ Important Reminder:</b>
Always practice proper risk management. Never risk more than 2% per trade. Start with a demo account if you're new.

<i>Built with precision by Blessing Omoregie (Nixiestone)</i>
<i>Where AI Meets Smart Money 💰</i>
"""
            
            await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
    
    async def cmd_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or "Unknown"
            
            # Check if already subscribed
            is_subscribed = await self.db.is_user_subscribed(user_id)
            
            if is_subscribed:
                await update.message.reply_text(
                    "You are already subscribed to trading signals.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Subscribe user
            await self.db.subscribe_user(user_id, username)
            
            message = """
<b>SUBSCRIPTION ACTIVATED</b>

You are now subscribed to Nixie's Trading Bot signals.

You will receive:
- High-probability trading signals
- Hourly market updates
- Signal performance tracking

<b>Signal Format Includes:</b>
- Entry price and type
- Stop Loss and Take Profit levels
- Risk:Reward ratio
- ML Confidence score
- Market conditions

Stay disciplined and follow risk management rules.

<i>Good luck with your trading</i>
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
                    "You are not currently subscribed.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Unsubscribe user
            await self.db.unsubscribe_user(user_id)
            
            message = """
<b>SUBSCRIPTION CANCELLED</b>

You have been unsubscribed from trading signals.

You will no longer receive:
- Trading signals
- Market updates

To resubscribe, use /subscribe command.

Thank you for using Nixie's Trading Bot.
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
            first_name = update.effective_user.first_name or "Trader"
            username = update.effective_user.username or "Unknown"
            
            # Get subscription status
            is_subscribed = await self.db.is_user_subscribed(user_id)
            subscription_date = await self.db.get_subscription_date(user_id)
            
            status_emoji = "✅" if is_subscribed else "❌"
            status_text = "ACTIVE" if is_subscribed else "INACTIVE"
            
            message = f"""
<b>📊 SUBSCRIPTION STATUS</b>

<b>Hello {first_name}!</b>

<b>Status:</b> {status_emoji} {status_text}
<b>User ID:</b> {user_id}
<b>Username:</b> @{username}
"""
            
            if is_subscribed and subscription_date:
                message += f"<b>Subscribed Since:</b> {subscription_date.strftime('%Y-%m-%d %H:%M UTC')}\n"
                days_subscribed = (datetime.now() - subscription_date).days
                message += f"<b>Days Active:</b> {days_subscribed} days\n"
            
            message += "\n"
            
            if is_subscribed:
                message += "<b>✓ You are receiving:</b>\n"
                message += "• High-probability trading signals\n"
                message += "• Hourly market updates\n"
                message += "• Real-time notifications\n"
                message += "• ML-enhanced predictions\n\n"
                message += "<i>Keep trading smart, {first_name}! 🚀</i>"
            else:
                message += "<b>⚠️ You are NOT subscribed</b>\n\n"
                message += "Use /subscribe to start receiving:\n"
                message += "• Trading signals\n"
                message += "• Market updates\n"
                message += "• Performance tracking\n\n"
                message += f"<i>Join us, {first_name}! 💪</i>"
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            # Get bot statistics
            total_signals = await self.db.get_signal_count()
            total_subscribers = await self.db.get_subscriber_count()
            
            # Get ML stats
            ml_stats = await self.main_bot.ml_engine.get_model_stats()
            
            # Get signal performance
            win_rate = await self.db.get_win_rate()
            avg_rr = await self.db.get_average_rr()
            
            message = f"""
<b>BOT STATISTICS</b>

<b>System Status:</b> {'ONLINE' if self.main_bot.running else 'OFFLINE'}

<b>Signal Statistics:</b>
- Total Signals: {total_signals}
- Win Rate: {win_rate:.1f}%
- Avg R:R: 1:{avg_rr:.2f}

<b>ML Engine:</b>
- Model Trained: {'Yes' if ml_stats.get('model_trained') else 'No'}
- Training Data: {ml_stats.get('total_signals', 0)} signals
- Next Training: {ml_stats.get('next_training', 0)} signals

<b>Community:</b>
- Active Subscribers: {total_subscribers}

<i>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            first_name = update.effective_user.first_name or "Trader"
            
            help_message = f"""
<b>📚 NIXIE'S TRADING BOT - HELP GUIDE</b>

<b>Hello {first_name}!</b> Here's everything you need to know:

<b>🤖 Bot Commands:</b>
/start - Welcome message and bot overview
/subscribe - Subscribe to trading signals
/unsubscribe - Unsubscribe from signals
/status - Check your subscription status
/stats - View bot performance statistics
/help - Show this help message

<b>📊 About Trading Signals:</b>
Signals are generated using Smart Money Concepts (SMC) strategy, focusing on institutional order flow patterns. 

<b>Each signal includes:</b>
• Symbol and Direction (BUY/SELL)
• Entry Price and Type (LIMIT/MARKET)
• Stop Loss (SL) in pips and price
• Take Profit (TP) in pips and price
• Risk:Reward Ratio (minimum 1:3)
• ML Confidence Score (0-100%)
• Signal Strength (LOW/MEDIUM/HIGH/VERY_HIGH)
• Market Conditions and Technical Data
• Setup Type (FVG, Order Block, Confluence)

<b>💰 Risk Management Rules:</b>
• Never risk more than 2% per trade
• Always use the provided stop losses
• Follow the Risk:Reward ratios exactly
• Trade only during recommended sessions (London/NY)
• Start with demo account if you're new

<b>🎯 Trading Strategy:</b>
The bot uses institutional precision scalping with:
• Multi-timeframe analysis (H4, H1, M5, M1)
• Liquidity sweep identification
• Order Block and Fair Value Gap detection
• Market structure analysis (BOS/ChoCH)
• Machine Learning signal enhancement
• Real-time scanning every 5 minutes

<b>📈 Expected Performance:</b>
• Target Win Rate: 65%+
• Minimum R:R: 1:3
• Typical Signals: 2-5 per day
• Hourly updates if no signals

<b>⚡ Pro Tips:</b>
• Be patient - quality over quantity
• High-probability setups are rare
• Trust the ML confidence scores
• Follow signals exactly as provided
• Review your trading journal regularly

<b>❓ Need More Help?</b>
Contact the developer or check the documentation.

<i>Trade smart, trade safe, {first_name}! 🚀</i>
<i>Author: Blessing Omoregie (Nixiestone)</i>
"""
            
            await update.message.reply_text(help_message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
    
    async def broadcast_signal(self, signal: Dict):
        """Broadcast trading signal to all subscribers"""
        try:
            message = self._format_signal_message(signal)
            subscribers = await self.db.get_subscribers()
            
            sent_count = 0
            failed_count = 0
            
            for subscriber in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=subscriber['user_id'],
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
                    sent_count += 1
                    await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Failed to send signal to {subscriber['user_id']}: {e}")
                    failed_count += 1
            
            logger.info(f"Signal broadcast complete. Sent: {sent_count}, Failed: {failed_count}")
            
        except Exception as e:
            logger.error(f"Error broadcasting signal: {e}", exc_info=True)
    
    async def broadcast_message(self, message: str):
        """Broadcast general message to all subscribers"""
        try:
            subscribers = await self.db.get_subscribers()
            
            if not subscribers:
                logger.warning("No subscribers to broadcast to")
                return
            
            for subscriber in subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=subscriber['user_id'],
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
                    await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Failed to send message to {subscriber['user_id']}: {e}")
            
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}", exc_info=True)
    
    def _format_signal_message(self, signal: Dict) -> str:
        """Format trading signal for Telegram"""
        timestamp = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')
        
        direction_emoji = "BUY" if signal['direction'] == 'BUY' else "SELL"
        
        message = f"""
<b>NEW TRADING SIGNAL</b>

<b>Symbol:</b> {signal['symbol']}
<b>Direction:</b> {direction_emoji}
<b>Signal Strength:</b> {signal['signal_strength']}

<b>ENTRY DETAILS:</b>
Entry Type: {signal['entry_type']}
Entry Price: {signal['entry_price']:.5f}

<b>RISK MANAGEMENT:</b>
Stop Loss: {signal['stop_loss']:.5f} ({signal['sl_pips']:.1f} pips)
Take Profit: {signal['take_profit']:.5f} ({signal['tp_pips']:.1f} pips)
Risk:Reward: 1:{signal['risk_reward']:.2f}

<b>TECHNICAL DATA:</b>
Setup: {signal['setup_type']}
ML Confidence: {signal['ml_confidence']:.1f}%
Current Price: {signal['current_price']:.5f}
ATR: {signal['atr']:.5f}
RSI: {signal['rsi']:.1f}

<b>MARKET CONDITIONS:</b>
Trend: {signal['trend']}
Bias: {signal['market_bias']}
Volatility: {signal['volatility']}

<b>Time Generated:</b> {timestamp}

<i>Follow strict risk management. Never risk more than 2% per trade.</i>
"""
        
        return message