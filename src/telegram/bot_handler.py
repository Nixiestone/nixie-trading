"""
Enhanced Telegram Bot Handler with User Account Management
"""
import os
import asyncio
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest
from datetime import datetime
from typing import Dict, List
from src.utils.logger import setup_logger
from src.utils.database import Database
from src.core.user_account_manager import MT5AccountManager, UserAccountSetupHandler

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
        
        # Account management
        self.account_manager = MT5AccountManager(config)
        self.setup_handler = UserAccountSetupHandler()
        
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
                
                # Basic commands
                self.app.add_handler(CommandHandler("start", self.cmd_start))
                self.app.add_handler(CommandHandler("subscribe", self.cmd_subscribe))
                self.app.add_handler(CommandHandler("unsubscribe", self.cmd_unsubscribe))
                self.app.add_handler(CommandHandler("status", self.cmd_status))
                self.app.add_handler(CommandHandler("stats", self.cmd_stats))
                self.app.add_handler(CommandHandler("help", self.cmd_help))
                self.app.add_handler(CommandHandler("autoexec", self.cmd_autoexec))
                
                # Account management commands (NEW)
                self.app.add_handler(CommandHandler("addaccount", self.cmd_add_account))
                self.app.add_handler(CommandHandler("myaccounts", self.cmd_my_accounts))
                self.app.add_handler(CommandHandler("cancel", self.cmd_cancel))
                
                # Admin-only commands (NEW)
                self.app.add_handler(CommandHandler("downloadcsv", self.cmd_download_csv))
                
                # Message handler for account setup
                self.app.add_handler(MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    self.handle_setup_message
                ))
                
                # Callback query handler for inline buttons
                self.app.add_handler(CallbackQueryHandler(self.handle_callback))
                
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
    
    # ==================== ACCOUNT MANAGEMENT COMMANDS ====================
    
    async def cmd_add_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addaccount command"""
        try:
            user_id = str(update.effective_user.id)
            
            # Check if user already has a pending setup
            if self.setup_handler.has_pending_setup(user_id):
                await update.message.reply_text(
                    "You already have an account setup in progress.\nUse /cancel to stop it.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Check if user can add more accounts
            can_add, message = self.account_manager.can_add_account(user_id)
            
            if not can_add:
                await update.message.reply_text(
                    f"❌ {message}\n\nUse /myaccounts to manage existing accounts.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Start setup process
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
            
            # Check if user has pending setup
            if not self.setup_handler.has_pending_setup(user_id):
                return  # Not in setup mode, ignore
            
            input_text = update.message.text.strip()
            
            # Process the input
            completed, message, account_data = self.setup_handler.process_input(user_id, input_text)
            
            # Send response
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            
            # If setup completed and confirmed
            if completed and account_data:
                # Add account to manager
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
        """Handle /myaccounts command - show user's accounts"""
        try:
            user_id = str(update.effective_user.id)
            
            # Get user's accounts
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
            
            # Create message with accounts
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
            
            # Add buttons for each account
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
            
            # Add "Add Account" button
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
                # Toggle account
                account_id = data.replace("toggle_", "")
                success, message = self.account_manager.toggle_account(user_id, account_id)
                
                if success:
                    # Refresh the accounts list
                    await self._refresh_accounts_list(query, user_id)
                    await query.message.reply_text(f"✅ {message}", parse_mode=ParseMode.HTML)
                else:
                    await query.message.reply_text(f"❌ {message}", parse_mode=ParseMode.HTML)
            
            elif data.startswith("delete_"):
                # Confirm deletion
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
                # Actually delete account
                account_id = data.replace("confirm_delete_", "")
                success, message = self.account_manager.remove_account(user_id, account_id)
                
                if success:
                    await query.message.edit_text(f"✅ {message}", parse_mode=ParseMode.HTML)
                    # Refresh the accounts list
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
        """Refresh the accounts list message"""
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
    
    # ==================== EXISTING COMMANDS (UPDATED) ====================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user_id = update.effective_user.id
            first_name = update.effective_user.first_name or "Trader"
            
            welcome_message = f"""
<b>👋 Hello {first_name}, Welcome to NIXIE'S TRADING BOT!</b>

🎯 <b>Enhanced Features:</b>
✓ High-precision SMC signals
✓ Multi-user MT5 auto-execution
✓ TP/SL hit notifications
✓ Secure account management
✓ Accurate win rate tracking

<b>📱 Commands:</b>
/subscribe - Get trading signals
/addaccount - Add your MT5 account
/myaccounts - Manage your accounts
/status - Check subscription
/stats - View performance stats
/help - Detailed help

<b>🔐 Your Accounts:</b>
Add up to 5 MT5 accounts for auto-execution!
Your credentials are encrypted and secure.

<i>Built by Blessing Omoregie (Nixiestone)</i>
"""
            
            await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
    
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

<b>💼 Account Management:</b>
/addaccount - Add MT5 account (max 5)
/myaccounts - Manage your accounts
/cancel - Cancel account setup

<b>👑 Admin Commands:</b>
/autoexec - Global auto-execution toggle

<b>🔐 How Account Management Works:</b>

1. <b>Adding Accounts:</b>
   • Use /addaccount to start
   • Follow the interactive setup
   • Provide: broker, server, login, password
   • Your password is encrypted

2. <b>Managing Accounts:</b>
   • Use /myaccounts to view all
   • Toggle auto-execution per account
   • Delete accounts you no longer need

3. <b>Security:</b>
   • All passwords are encrypted
   • Only you can access your accounts
   • Each account is isolated
   • Delete anytime

<b>🚀 Auto-Execution:</b>
When enabled, signals are automatically executed on YOUR accounts with YOUR funds. Make sure you understand the risks!

<i>Trade smart, {first_name}! 🚀</i>
"""
        
        await update.message.reply_text(help_message, parse_mode=ParseMode.HTML)
    
    # Keep other existing methods (subscribe, unsubscribe, status, autoexec, etc.)
    # ... [Previous methods remain the same]
    
    async def cmd_download_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /downloadcsv command - Admin only"""
        try:
            user_id = str(update.effective_user.id)
            
            # Check if admin
            if user_id != self.config.TELEGRAM_ADMIN_ID:
                await update.message.reply_text(
                    "⛔ This command is only available to the admin.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Check which CSV to download
            if context.args:
                csv_type = context.args[0].lower()
            else:
                # Show options
                keyboard = [
                    [InlineKeyboardButton("📊 Signals Log", callback_data="download_signals")],
                    [InlineKeyboardButton("✅ Closed Trades", callback_data="download_closed")],
                    [InlineKeyboardButton("📥 Both Files", callback_data="download_both")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "<b>📥 DOWNLOAD CSV FILES</b>\n\n"
                    "Select which CSV file(s) to download:",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                return
            
            # Download based on argument
            if csv_type == 'signals':
                await self._send_csv_file(update, 'data/signals_log.csv', 'Signals Log')
            elif csv_type == 'closed':
                await self._send_csv_file(update, 'data/closed_trades.csv', 'Closed Trades')
            elif csv_type == 'both':
                await self._send_csv_file(update, 'data/signals_log.csv', 'Signals Log')
                await asyncio.sleep(1)
                await self._send_csv_file(update, 'data/closed_trades.csv', 'Closed Trades')
            else:
                await update.message.reply_text(
                    "Usage: /downloadcsv [signals|closed|both]",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"Error in downloadcsv command: {e}")
            await update.message.reply_text("An error occurred while downloading CSV.")
    
    async def _send_csv_file(self, update, filepath: str, file_description: str):
        """Send CSV file to user"""
        try:
            if not os.path.exists(filepath):
                await update.message.reply_text(
                    f"❌ {file_description} file not found. No data yet.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Get file size
            file_size = os.path.getsize(filepath)
            file_size_mb = file_size / (1024 * 1024)
            
            # Send file
            with open(filepath, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(filepath),
                    caption=f"<b>📥 {file_description}</b>\n\n"
                            f"Size: {file_size_mb:.2f} MB\n"
                            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    parse_mode=ParseMode.HTML
                )
            
            logger.info(f"Admin downloaded {file_description} CSV")
            
        except Exception as e:
            logger.error(f"Error sending CSV file: {e}")
            await update.message.reply_text(
                f"❌ Error sending {file_description} file.",
                parse_mode=ParseMode.HTML
            )
    
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
            # Get account nickname from account manager
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
    
    async def cmd_autoexec(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /autoexec command - deprecated but kept for compatibility"""
        try:
            await update.message.reply_text(
                "<b>ℹ️ AUTO-EXECUTION INFO</b>\n\n"
                "Auto-execution is now managed per-account!\n\n"
                "Use /myaccounts to enable/disable auto-execution for each of your MT5 accounts.\n\n"
                "Each user controls their own accounts independently.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error in autoexec command: {e}")