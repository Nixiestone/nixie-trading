"""
Enhanced Telegram Bot Handler with User Account Management
"""

import os
import asyncio
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from src.telegram.pdf_generator import PDFGenerator
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
        self.pdf_generator = PDFGenerator()
        
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
                self.app.add_handler(CommandHandler("downloadsignals", self.cmd_download_signals))
                self.app.add_handler(CommandHandler("downloadclosed", self.cmd_download_closed))
                
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
                "❌ Failed to generate PDF. Check if signals exist.",
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
                "❌ Failed to generate PDF. Check if closed trades exist.",
                parse_mode=ParseMode.HTML
            )
        
    except Exception as e:
        logger.error(f"Error in download closed command: {e}")
        await update.message.reply_text("❌ An error occurred generating the PDF.")
    
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
    