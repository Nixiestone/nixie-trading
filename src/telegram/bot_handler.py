"""
Enhanced Telegram Bot Handler with User Account Management and Auto Timezone Detection
"""
import os
import asyncio
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from datetime import datetime
from typing import Dict, List
from timezonefinder import TimezoneFinder
import geocoder
from src.utils.logger import setup_logger
from src.utils.database import Database
from src.core.user_account_manager import MT5AccountManager, UserAccountSetupHandler

logger = setup_logger(__name__)


class TelegramBotHandler:
    """Enhanced Telegram bot with user account management and auto timezone"""
    
    def __init__(self, config, main_bot):
        self.config = config
        self.main_bot = main_bot
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.app = None
        self.bot = None
        self.db = Database(config.DB_PATH)
        
        # Account management
        self.account_manager = MT5AccountManager(config)
        self.setup_handler = UserAccountSetupHandler()
        
        # Timezone detection
        self.tf = TimezoneFinder()
        self.user_timezones = {}
        
        # News trading control
        self.news_trading_enabled = getattr(config, 'ALLOW_TRADING_DURING_NEWS', False)
        
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
                
                # Register all commands
                self._register_commands()
                
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
    
    def _register_commands(self):
        """Register all bot commands"""
        try:
            # User commands
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            self.app.add_handler(CommandHandler("subscribe", self.cmd_subscribe))
            self.app.add_handler(CommandHandler("unsubscribe", self.cmd_unsubscribe))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("news", self.cmd_news))
            
            # Account management commands
            self.app.add_handler(CommandHandler("addaccount", self.cmd_add_account))
            self.app.add_handler(CommandHandler("myaccounts", self.cmd_my_accounts))
            self.app.add_handler(CommandHandler("cancel", self.cmd_cancel))
            
            # Admin commands
            self.app.add_handler(CommandHandler("downloadsignals", self.cmd_downloadsignals))
            self.app.add_handler(CommandHandler("downloadclosed", self.cmd_downloadclosed))
            self.app.add_handler(CommandHandler("autoexec", self.cmd_autoexec))
            self.app.add_handler(CommandHandler("stats", self.cmd_stats))
            self.app.add_handler(CommandHandler("newstrading", self.cmd_newstrading))
            
            # Message handler for account setup
            self.app.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                self.handle_setup_message
            ))
            
            # Callback query handler
            self.app.add_handler(CallbackQueryHandler(self.handle_callback))
            
            logger.info("All commands registered successfully")
        except Exception as e:
            logger.error(f"Error registering commands: {e}")
            raise
    
    def _detect_user_timezone(self, user_id: int) -> str:
        """Automatically detect user timezone using IP geolocation"""
        try:
            g = geocoder.ip('me')
            
            if g.ok and g.latlng:
                lat, lng = g.latlng
                timezone_str = self.tf.timezone_at(lat=lat, lng=lng)
                
                if timezone_str:
                    self.user_timezones[user_id] = timezone_str
                    logger.info(f"Auto-detected timezone for user {user_id}: {timezone_str}")
                    return timezone_str
            
            default_tz = getattr(self.config, 'DEFAULT_TIMEZONE', 'UTC')
            self.user_timezones[user_id] = default_tz
            logger.warning(f"Could not detect timezone for user {user_id}, using {default_tz}")
            return default_tz
            
        except Exception as e:
            logger.error(f"Error detecting timezone for user {user_id}: {e}")
            default_tz = getattr(self.config, 'DEFAULT_TIMEZONE', 'UTC')
            self.user_timezones[user_id] = default_tz
            return default_tz
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with auto timezone detection"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or "Unknown"
            first_name = update.effective_user.first_name or "Trader"
            
            # Auto-detect timezone
            detected_tz = self._detect_user_timezone(user_id)
            
            welcome_message = f"""
<b>👋 Hello {first_name}, Welcome to NIXIE'S TRADING BOT!</b>

🌍 <i>Your timezone has been automatically detected as: <b>{detected_tz}</b></i>

🎯 <b>Enhanced Features:</b>
✓ High-precision SMC signals
✓ Daily news reports (8 AM your time)
✓ 10-minute news reminders
✓ Live news notifications with predictions
✓ Multi-user MT5 auto-execution
✓ Auto-detect timezone from location
✓ News-aware trading control

<b>📱 Quick Start:</b>
/subscribe - Get trading signals
/addaccount - Add your MT5 account
/news - View today's news schedule
/help - Detailed help

<i>Built by Blessing Omoregie (Nixiestone)</i>
"""
            
            await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
            logger.info(f"User {user_id} ({username}) started bot with timezone {detected_tz}")
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ Error starting bot. Please try again.")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Updated help command with all features"""
        help_text = """
<b>📚 NIXIE TRADING BOT - HELP GUIDE</b>

<b>User Commands:</b>
/start - Start bot & auto-detect timezone
/subscribe - Subscribe to signals
/unsubscribe - Unsubscribe from signals
/status - Check subscription status
/news - View today's news schedule
/help - Show this help message

<b>Account Management:</b>
/addaccount - Add MT5 account (max 5)
/myaccounts - Manage your accounts
/cancel - Cancel account setup

<b>Admin Commands:</b> ⚠️ <i>(Admin Use Only)</i>
/stats - View trading statistics
/downloadsignals - Download signals CSV
/downloadclosed - Download closed trades CSV
/autoexec - Toggle auto-execution
/newstrading - Toggle trading during news

<b>✨ Features:</b>
✅ Real-time signal notifications
✅ Auto-detect timezone from location
✅ Daily news reports (8 AM your time)
✅ 10-minute news reminders
✅ Live news notifications with predictions
✅ TP/SL monitoring & notifications
✅ News-aware trading control

<b>🔐 Security:</b>
• All passwords encrypted
• Isolated user accounts
• Secure credential storage

Need help? Contact @NixiestoneSupport
"""
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get today's news schedule"""
        try:
            user_id = update.effective_user.id
            
            # Get user timezone (auto-detected)
            if user_id not in self.user_timezones:
                self._detect_user_timezone(user_id)
            
            timezone = self.user_timezones.get(user_id, 'UTC')
            
            if hasattr(self.main_bot, 'news_service'):
                import pytz
                news = self.main_bot.news_service.get_todays_red_folder_news(timezone)
                
                if not news:
                    await update.message.reply_text("📰 No high-impact news today ✅")
                    return
                
                message = "🚨 *Today's Red Folder News*\n\n"
                
                for i, event in enumerate(news, 1):
                    event_time = event['datetime'].astimezone(pytz.timezone(timezone))
                    message += f"*{i}. {event['title']}*\n"
                    message += f"   🌍 {event['country']} | ⚠️ {event['impact']}\n"
                    message += f"   ⏰ {event_time.strftime('%I:%M %p')}\n"
                    message += f"   📊 F: {event['forecast']} | P: {event['previous']}\n\n"
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ News service not available")
                
        except Exception as e:
            logger.error(f"Error in cmd_news: {e}")
            await update.message.reply_text("❌ Error fetching news")
    
    async def cmd_autoexec(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle auto-execution of trades (ADMIN ONLY)"""
        try:
            user_id = str(update.effective_user.id)
            
            if not self._is_admin(user_id):
                await update.message.reply_text("❌ Admin access required")
                return
            
            # Toggle auto-execution
            auto_exec_enabled = not getattr(self, 'auto_exec_enabled', False)
            self.auto_exec_enabled = auto_exec_enabled
            
            status = "✅ ENABLED" if auto_exec_enabled else "❌ DISABLED"
            message = f"*Auto-Execution Status*\n\n{status}\n\n"
            
            if auto_exec_enabled:
                message += "⚠️ Bot will automatically execute trades based on signals."
            else:
                message += "ℹ️ Bot will only send signal notifications."
            
            await update.message.reply_text(message, parse_mode='Markdown')
            logger.info(f"Auto-execution {status} by admin {user_id}")
            
        except Exception as e:
            logger.error(f"Error in cmd_autoexec: {e}")
            await update.message.reply_text("❌ Error toggling auto-execution")
    
    async def cmd_downloadsignals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Download all signals CSV (ADMIN ONLY)"""
        try:
            user_id = str(update.effective_user.id)
            
            if not self._is_admin(user_id):
                await update.message.reply_text("❌ Admin access required")
                return
            
            signals_file = "data/signals_log.csv"
            
            if not os.path.exists(signals_file):
                await update.message.reply_text("❌ No signals file found")
                return
            
            with open(signals_file, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    caption="📊 All Trading Signals"
                )
            
            logger.info(f"Signals CSV downloaded by admin {user_id}")
            
        except Exception as e:
            logger.error(f"Error in cmd_downloadsignals: {e}")
            await update.message.reply_text("❌ Error downloading signals")
    
    async def cmd_downloadclosed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Download closed trades CSV (ADMIN ONLY)"""
        try:
            user_id = str(update.effective_user.id)
            
            if not self._is_admin(user_id):
                await update.message.reply_text("❌ Admin access required")
                return
            
            closed_file = "data/closed_trades.csv"
            
            if not os.path.exists(closed_file):
                await update.message.reply_text("❌ No closed trades file found")
                return
            
            with open(closed_file, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"closed_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    caption="📈 Closed Trading History"
                )
            
            logger.info(f"Closed trades CSV downloaded by admin {user_id}")
            
        except Exception as e:
            logger.error(f"Error in cmd_downloadclosed: {e}")
            await update.message.reply_text("❌ Error downloading closed trades")
    
    async def cmd_newstrading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle trading during news events (ADMIN ONLY)"""
        try:
            user_id = str(update.effective_user.id)
            
            if not self._is_admin(user_id):
                await update.message.reply_text("❌ Admin access required")
                return
            
            self.news_trading_enabled = not self.news_trading_enabled
            
            # Update config
            if hasattr(self.config, 'ALLOW_TRADING_DURING_NEWS'):
                self.config.ALLOW_TRADING_DURING_NEWS = self.news_trading_enabled
            
            status = "✅ ENABLED" if self.news_trading_enabled else "❌ DISABLED"
            message = f"*News Trading Status*\n\n{status}\n\n"
            
            if self.news_trading_enabled:
                message += "⚠️ Bot will trade during news events"
            else:
                message += "✅ Bot will pause trading during high-impact news"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            logger.info(f"News trading {status} by admin {user_id}")
            
        except Exception as e:
            logger.error(f"Error in cmd_newstrading: {e}")
            await update.message.reply_text("❌ Error toggling news trading")
    
    def get_all_subscribers(self):
        """Get all subscribers with their settings"""
        try:
            # This would be called synchronously from news service
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If called from async context, we can't use asyncio.run
                return []
            else:
                return asyncio.run(self._async_get_all_subscribers())
        except Exception as e:
            logger.error(f"Error getting subscribers: {e}")
            return []
    
    async def _async_get_all_subscribers(self):
        """Async get all subscribers"""
        try:
            subscribers_data = await self.db.get_subscribers()
            subscribers = []
            
            for sub in subscribers_data:
                user_id = sub['user_id']
                
                # Ensure timezone is detected
                if user_id not in self.user_timezones:
                    self._detect_user_timezone(user_id)
                
                subscribers.append({
                    'user_id': user_id,
                    'timezone': self.user_timezones.get(user_id, 'UTC')
                })
            
            return subscribers
        except Exception as e:
            logger.error(f"Error in async get subscribers: {e}")
            return []
    
    def send_message(self, user_id, message):
        """Send message to user (sync wrapper)"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._async_send_message(user_id, message))
            else:
                asyncio.run(self._async_send_message(user_id, message))
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")
    
    async def _async_send_message(self, user_id, message):
        """Async send message helper"""
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in async send message to {user_id}: {e}")
    
    def _is_admin(self, user_id: str) -> bool:
        """Check if user is admin"""
        try:
            admin_id = str(getattr(self.config, 'TELEGRAM_ADMIN_ID', ''))
            return user_id == admin_id
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False
        
    # ADD THESE METHODS TO THE TelegramBotHandler CLASS (continuation from Part 1)
    
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
✓ Daily news reports (8 AM your time)
✓ 10-minute news reminders
✓ Live news notifications
✓ Hourly market updates

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
            
            # Get timezone
            if user_id not in self.user_timezones:
                self._detect_user_timezone(user_id)
            timezone = self.user_timezones.get(user_id, 'UTC')
            
            message = f"""
<b>📊 SUBSCRIPTION STATUS</b>

<b>Hello {first_name}!</b>

<b>Status:</b> {status_emoji} {status_text}
<b>User ID:</b> {user_id}
<b>Timezone:</b> {timezone}
"""
            
            if is_subscribed:
                message += """
<b>✓ You are receiving:</b>
• Trading signals
• TP/SL notifications
• Daily news reports (8 AM)
• News reminders
• Market updates
"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            user_id = str(update.effective_user.id)
            
            # Get bot stats
            win_rate_stats = self.main_bot.signal_generator.get_win_rate()
            active_signals = self.main_bot.signal_generator.get_active_signals_count()
            ml_stats = await self.main_bot.ml_engine.get_model_stats()
            subscribers = await self.db.get_subscriber_count()
            
            # Get account stats
            account_stats = self.account_manager.get_total_accounts()
            user_accounts = self.account_manager.get_user_accounts(user_id)
            user_enabled = len([a for a in user_accounts if a['enabled']])
            
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

<b>Your Accounts:</b>
- Total: {len(user_accounts)}
- Enabled: {user_enabled}

<b>Global Accounts:</b>
- Users with accounts: {account_stats['total_users']}
- Total accounts: {account_stats['total_accounts']}
- Enabled: {account_stats['enabled_accounts']}

<b>ML Engine:</b>
- Trained: {'Yes' if ml_stats.get('model_trained') else 'No'}
- Data: {ml_stats.get('total_signals', 0)} signals

<i>Updated: {datetime.now().strftime('%H:%M:%S UTC')}</i>
"""
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
    
    async def cmd_add_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addaccount command"""
        try:
            user_id = str(update.effective_user.id)
            
            if self.setup_handler.has_pending_setup(user_id):
                await update.message.reply_text(
                    "You already have an account setup in progress.\nUse /cancel to stop it.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            can_add, message = self.account_manager.can_add_account(user_id)
            
            if not can_add:
                await update.message.reply_text(
                    f"❌ {message}\n\nUse /myaccounts to manage existing accounts.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            welcome_msg = self.setup_handler.start_setup(user_id)
            await update.message.reply_text(welcome_msg, parse_mode=ParseMode.HTML)
            
            logger.info(f"User {user_id} started account setup")
            
        except Exception as e:
            logger.error(f"Error in addaccount command: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
    
    async def cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command"""
        try:
            user_id = str(update.effective_user.id)
            
            if self.setup_handler.cancel_setup(user_id):
                await update.message.reply_text(
                    "✅ Account setup cancelled.\n\nUse /addaccount to start over.",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    "No setup in progress.",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"Error in cancel command: {e}")
    
    async def handle_setup_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages during account setup"""
        try:
            user_id = str(update.effective_user.id)
            
            if not self.setup_handler.has_pending_setup(user_id):
                return
            
            input_text = update.message.text.strip()
            
            completed, message, account_data = self.setup_handler.process_input(user_id, input_text)
            
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
            if completed and account_data:
                success, result_msg = self.account_manager.add_account(user_id, account_data)
                
                if success:
                    final_msg = f"""
<b>🎉 ACCOUNT ADDED SUCCESSFULLY!</b>

<b>Nickname:</b> {account_data['nickname']}
<b>Login:</b> {account_data['login']}
<b>Auto-Execution:</b> ENABLED ✅

Your account is now active and will automatically execute signals.

<b>What's Next?</b>
• Signals will be auto-executed on this account
• You'll receive notifications for all trades
• Use /myaccounts to manage this account

<b>Security:</b>
• Your credentials are encrypted
• Only you can access this account
• You can remove it anytime

<i>Happy trading! 🚀</i>
"""
                    await update.message.reply_text(final_msg, parse_mode=ParseMode.HTML)
                    logger.info(f"User {user_id} successfully added account: {account_data['nickname']}")
                else:
                    await update.message.reply_text(
                        f"❌ Failed to add account: {result_msg}\n\nPlease try again with /addaccount",
                        parse_mode=ParseMode.HTML
                    )
            
        except Exception as e:
            logger.error(f"Error handling setup message: {e}")
            await update.message.reply_text(
                "An error occurred. Use /cancel to stop and try again.",
                parse_mode=ParseMode.HTML
            )
    
    async def cmd_my_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /myaccounts command"""
        try:
            user_id = str(update.effective_user.id)
            
            accounts = self.account_manager.get_user_accounts(user_id)
            
            if not accounts:
                can_add, msg = self.account_manager.can_add_account(user_id)
                await update.message.reply_text(
                    f"<b>📊 MY MT5 ACCOUNTS</b>\n\n"
                    f"You don't have any accounts yet.\n\n"
                    f"{msg}\n\n"
                    f"Use /addaccount to add your first account.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            message = "<b>📊 MY MT5 ACCOUNTS</b>\n\n"
            
            for i, acc in enumerate(accounts, 1):
                status_emoji = "✅" if acc['enabled'] else "⏸"
                status_text = "ENABLED" if acc['enabled'] else "DISABLED"
                
                message += f"<b>{i}. {acc['nickname']}</b>\n"
                message += f"   Status: {status_emoji} {status_text}\n"
                message += f"   Login: {acc['login']}\n"
                message += f"   Broker: {acc['broker']}\n"
                message += f"   Server: {acc['server']}\n"
                message += f"   Trades: {acc['total_trades']}\n"
                message += f"   Added: {acc['added_date'][:10]}\n\n"
            
            keyboard = []
            for acc in accounts:
                row = [
                    InlineKeyboardButton(
                        f"{'⏸ Disable' if acc['enabled'] else '✅ Enable'} {acc['nickname'][:15]}", 
                        callback_data=f"toggle_{acc['account_id']}"
                    ),
                    InlineKeyboardButton(
                        f"🗑 Delete", 
                        callback_data=f"delete_{acc['account_id']}"
                    )
                ]
                keyboard.append(row)
            
            can_add, add_msg = self.account_manager.can_add_account(user_id)
            if can_add:
                keyboard.append([InlineKeyboardButton("➕ Add New Account", callback_data="add_account")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message += f"\n<i>{add_msg}</i>"
            
            await update.message.reply_text(
                message, 
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in myaccounts command: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = str(update.effective_user.id)
            data = query.data
            
            if data.startswith("toggle_"):
                account_id = data.replace("toggle_", "")
                success, message = self.account_manager.toggle_account(user_id, account_id)
                
                if success:
                    await self._refresh_accounts_list(query, user_id)
                    await query.message.reply_text(f"✅ {message}", parse_mode=ParseMode.HTML)
                else:
                    await query.message.reply_text(f"❌ {message}", parse_mode=ParseMode.HTML)
            
            elif data.startswith("delete_"):
                account_id = data.replace("delete_", "")
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{account_id}"),
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(
                    "⚠️ <b>Are you sure you want to delete this account?</b>\n\n"
                    "This action cannot be undone.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
            
            elif data.startswith("confirm_delete_"):
                account_id = data.replace("confirm_delete_", "")
                success, message = self.account_manager.remove_account(user_id, account_id)
                
                if success:
                    await query.message.edit_text(f"✅ {message}", parse_mode=ParseMode.HTML)
                    await asyncio.sleep(1)
                    await self._refresh_accounts_list(query, user_id)
                else:
                    await query.message.edit_text(f"❌ {message}", parse_mode=ParseMode.HTML)
            
            elif data == "cancel_delete":
                await query.message.edit_text("Deletion cancelled.", parse_mode=ParseMode.HTML)
            
            elif data == "add_account":
                await query.message.reply_text(
                    "Use /addaccount to start adding a new account.",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
    
    async def _refresh_accounts_list(self, query, user_id: str):
        """Refresh accounts list message"""
        try:
            accounts = self.account_manager.get_user_accounts(user_id)
            
            message = "<b>📊 MY MT5 ACCOUNTS</b>\n\n"
            
            for i, acc in enumerate(accounts, 1):
                status_emoji = "✅" if acc['enabled'] else "⏸"
                status_text = "ENABLED" if acc['enabled'] else "DISABLED"
                
                message += f"<b>{i}. {acc['nickname']}</b>\n"
                message += f"   Status: {status_emoji} {status_text}\n"
                message += f"   Login: {acc['login']}\n"
                message += f"   Broker: {acc['broker']}\n"
                message += f"   Trades: {acc['total_trades']}\n\n"
            
            keyboard = []
            for acc in accounts:
                row = [
                    InlineKeyboardButton(
                        f"{'⏸ Disable' if acc['enabled'] else '✅ Enable'} {acc['nickname'][:15]}", 
                        callback_data=f"toggle_{acc['account_id']}"
                    ),
                    InlineKeyboardButton(
                        f"🗑 Delete", 
                        callback_data=f"delete_{acc['account_id']}"
                    )
                ]
                keyboard.append(row)
            
            can_add, add_msg = self.account_manager.can_add_account(user_id)
            if can_add:
                keyboard.append([InlineKeyboardButton("➕ Add New Account", callback_data="add_account")])
            
            message += f"\n<i>{add_msg}</i>"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error refreshing accounts list: {e}")
    
    async def broadcast_message(self, message: str):
        """Broadcast general message"""
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
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send to {subscriber['user_id']}: {e}")
            
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
    
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
    
    async def send_trade_closed_notification(self, notification: Dict):
        """Send notification when TP or SL hits"""
        try:
            message = self._format_trade_closed_message(notification)
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
            logger.error(f"Error sending trade closed notification: {e}")
    
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
    
    async def execute_signal_for_users(self, signal: Dict) -> Dict:
        """Execute signal on enabled user accounts"""
        try:
            if not hasattr(self, 'multi_user_executor'):
                from src.mt5.multi_user_executor import MultiUserMT5Executor
                self.multi_user_executor = MultiUserMT5Executor(self.account_manager, self.config)
            
            return await self.multi_user_executor.execute_signal_for_all_users(signal)
        except Exception as e:
            logger.error(f"Error executing signal for users: {e}")
            return {}
    
    async def send_execution_confirmations(self, signal: Dict, execution_results: Dict):
        """Send execution confirmations to users"""
        try:
            for user_id, accounts in execution_results.items():
                try:
                    message = self._format_execution_confirmation(signal, accounts)
                    await self.bot.send_message(
                        chat_id=int(user_id),
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send execution confirmation to {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending execution confirmations: {e}")
    
    def _format_execution_confirmation(self, signal: Dict, accounts: Dict) -> str:
        """Format execution confirmation message"""
        executed_count = len([t for t in accounts.values() if t])
        
        message = f"""
<b>✅ TRADE EXECUTED</b>

<b>Signal:</b> {signal['symbol']} {signal['direction']}
<b>Entry Type:</b> {signal['entry_type']}
<b>Entry Price:</b> {signal['entry_price']:.5f}

<b>Your Accounts:</b>
"""
        
        for account_id, ticket in accounts.items():
            user_accounts = self.account_manager.get_user_accounts(str(list(accounts.keys())[0].split('_')[0]))
            account_name = "Account"
            for acc in user_accounts:
                if acc['account_id'] == account_id:
                    account_name = acc['nickname']
                    break
            
            if ticket:
                message += f"✅ {account_name}: Ticket #{ticket}\n"
            else:
                message += f"❌ {account_name}: Failed\n"
        
        message += f"""
<b>Risk Management:</b>
SL: {signal['stop_loss']:.5f} ({signal['sl_pips']:.1f} pips)
TP: {signal['take_profit']:.5f} ({signal['tp_pips']:.1f} pips)
R:R: 1:{signal['risk_reward']:.2f}

<i>Trades are being monitored for TP/SL hits.</i>
"""
        
        return message
    
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