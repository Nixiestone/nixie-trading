"""
Multi-User MT5 Account Manager
Allows users to add their own MT5 accounts for auto-execution
Secure credential storage with encryption
"""

import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MT5AccountManager:
    """Manages multiple user MT5 accounts with secure storage"""
    
    def __init__(self, config):
        self.config = config
        self.accounts_file = 'data/user_accounts.encrypted'
        self.key_file = 'data/.encryption_key'
        self.cipher = None
        self.user_accounts = {}  # {user_id: [accounts]}
        
        # Initialize encryption
        self._initialize_encryption()
        
        # Load existing accounts
        self._load_accounts()
    
    def _initialize_encryption(self):
        """Initialize encryption key"""
        try:
            if os.path.exists(self.key_file):
                # Load existing key
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                # Set file permissions to read-only for owner
                os.chmod(self.key_file, 0o600)
            
            self.cipher = Fernet(key)
            logger.info("Encryption initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing encryption: {e}")
            raise
    
    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode())
    
    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data).decode()
    
    def _load_accounts(self):
        """Load user accounts from encrypted file"""
        try:
            if os.path.exists(self.accounts_file):
                with open(self.accounts_file, 'rb') as f:
                    encrypted_data = f.read()
                
                if encrypted_data:
                    decrypted_data = self._decrypt_data(encrypted_data)
                    self.user_accounts = json.loads(decrypted_data)
                    logger.info(f"Loaded accounts for {len(self.user_accounts)} users")
            else:
                self.user_accounts = {}
                logger.info("No existing accounts file - starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading accounts: {e}")
            self.user_accounts = {}
    
    def _save_accounts(self):
        """Save user accounts to encrypted file"""
        try:
            # Convert to JSON
            json_data = json.dumps(self.user_accounts, indent=2)
            
            # Encrypt
            encrypted_data = self._encrypt_data(json_data)
            
            # Save to file
            os.makedirs(os.path.dirname(self.accounts_file), exist_ok=True)
            with open(self.accounts_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set file permissions
            os.chmod(self.accounts_file, 0o600)
            
            logger.info("User accounts saved securely")
            
        except Exception as e:
            logger.error(f"Error saving accounts: {e}")
    
    def can_add_account(self, user_id: str) -> tuple:
        """Check if user can add more accounts"""
        is_admin = user_id == self.config.TELEGRAM_ADMIN_ID
        
        if is_admin:
            return True, "Admin - unlimited accounts"
        
        current_count = len(self.user_accounts.get(user_id, []))
        max_accounts = 5
        
        if current_count >= max_accounts:
            return False, f"Maximum {max_accounts} accounts per user"
        
        return True, f"Can add {max_accounts - current_count} more account(s)"
    
    def add_account(self, user_id: str, account_data: Dict) -> tuple:
        """Add MT5 account for user"""
        try:
            # Check if user can add more accounts
            can_add, message = self.can_add_account(user_id)
            if not can_add:
                return False, message
            
            # Validate account data
            required_fields = ['login', 'password', 'server', 'broker', 'nickname']
            missing = [f for f in required_fields if f not in account_data]
            
            if missing:
                return False, f"Missing fields: {', '.join(missing)}"
            
            # Initialize user's account list if needed
            if user_id not in self.user_accounts:
                self.user_accounts[user_id] = []
            
            # Check for duplicate login
            for acc in self.user_accounts[user_id]:
                if acc['login'] == account_data['login']:
                    return False, f"Account {account_data['login']} already added"
            
            # Generate unique account ID
            account_id = f"{user_id}_{account_data['login']}_{int(datetime.now().timestamp())}"
            
            # Create account entry
            account = {
                'account_id': account_id,
                'login': account_data['login'],
                'password': account_data['password'],  # Will be encrypted when saved
                'server': account_data['server'],
                'broker': account_data['broker'],
                'nickname': account_data['nickname'],
                'enabled': True,  # Auto-execution enabled by default
                'added_date': datetime.now().isoformat(),
                'last_used': None,
                'total_trades': 0
            }
            
            # Add to user's accounts
            self.user_accounts[user_id].append(account)
            
            # Save to encrypted file
            self._save_accounts()
            
            logger.info(f"Account added for user {user_id}: {account['nickname']} ({account['login']})")
            
            return True, f"Account '{account['nickname']}' added successfully!"
            
        except Exception as e:
            logger.error(f"Error adding account: {e}")
            return False, f"Error: {str(e)}"
    
    def remove_account(self, user_id: str, account_id: str) -> tuple:
        """Remove MT5 account"""
        try:
            if user_id not in self.user_accounts:
                return False, "No accounts found"
            
            # Find and remove account
            accounts = self.user_accounts[user_id]
            for i, acc in enumerate(accounts):
                if acc['account_id'] == account_id:
                    removed_nickname = acc['nickname']
                    del accounts[i]
                    
                    # Remove user entry if no accounts left
                    if not accounts:
                        del self.user_accounts[user_id]
                    
                    self._save_accounts()
                    
                    logger.info(f"Account removed for user {user_id}: {removed_nickname}")
                    return True, f"Account '{removed_nickname}' removed successfully"
            
            return False, "Account not found"
            
        except Exception as e:
            logger.error(f"Error removing account: {e}")
            return False, f"Error: {str(e)}"
    
    def toggle_account(self, user_id: str, account_id: str) -> tuple:
        """Toggle auto-execution for an account"""
        try:
            if user_id not in self.user_accounts:
                return False, "No accounts found"
            
            for acc in self.user_accounts[user_id]:
                if acc['account_id'] == account_id:
                    acc['enabled'] = not acc['enabled']
                    self._save_accounts()
                    
                    status = "enabled" if acc['enabled'] else "disabled"
                    logger.info(f"Account {acc['nickname']} {status} for user {user_id}")
                    
                    return True, f"Auto-execution {status} for '{acc['nickname']}'"
            
            return False, "Account not found"
            
        except Exception as e:
            logger.error(f"Error toggling account: {e}")
            return False, f"Error: {str(e)}"
    
    def get_user_accounts(self, user_id: str) -> List[Dict]:
        """Get all accounts for a user"""
        accounts = self.user_accounts.get(user_id, [])
        
        # Return sanitized version (without passwords)
        return [{
            'account_id': acc['account_id'],
            'login': acc['login'],
            'server': acc['server'],
            'broker': acc['broker'],
            'nickname': acc['nickname'],
            'enabled': acc['enabled'],
            'added_date': acc['added_date'],
            'total_trades': acc['total_trades']
        } for acc in accounts]
    
    def get_account_credentials(self, user_id: str, account_id: str) -> Optional[Dict]:
        """Get full account credentials (including password) for execution"""
        if user_id not in self.user_accounts:
            return None
        
        for acc in self.user_accounts[user_id]:
            if acc['account_id'] == account_id and acc['enabled']:
                return {
                    'login': int(acc['login']),
                    'password': acc['password'],
                    'server': acc['server']
                }
        
        return None
    
    def get_enabled_accounts(self, user_id: str) -> List[Dict]:
        """Get all enabled accounts for a user"""
        if user_id not in self.user_accounts:
            return []
        
        return [acc for acc in self.user_accounts[user_id] if acc['enabled']]
    
    def increment_trade_count(self, user_id: str, account_id: str):
        """Increment trade count for an account"""
        try:
            if user_id in self.user_accounts:
                for acc in self.user_accounts[user_id]:
                    if acc['account_id'] == account_id:
                        acc['total_trades'] += 1
                        acc['last_used'] = datetime.now().isoformat()
                        self._save_accounts()
                        break
        except Exception as e:
            logger.error(f"Error incrementing trade count: {e}")
    
    def get_all_enabled_accounts(self) -> Dict[str, List[Dict]]:
        """Get all enabled accounts across all users"""
        enabled_accounts = {}
        
        for user_id, accounts in self.user_accounts.items():
            enabled = [acc for acc in accounts if acc['enabled']]
            if enabled:
                enabled_accounts[user_id] = enabled
        
        return enabled_accounts
    
    def get_total_accounts(self) -> Dict:
        """Get statistics about accounts"""
        total_users = len(self.user_accounts)
        total_accounts = sum(len(accs) for accs in self.user_accounts.values())
        enabled_accounts = sum(
            len([a for a in accs if a['enabled']]) 
            for accs in self.user_accounts.values()
        )
        
        return {
            'total_users': total_users,
            'total_accounts': total_accounts,
            'enabled_accounts': enabled_accounts,
            'disabled_accounts': total_accounts - enabled_accounts
        }


class UserAccountSetupHandler:
    """Handles interactive account setup via Telegram"""
    
    def __init__(self):
        self.pending_setups = {}  # {user_id: {step: str, data: {}}}
    
    def start_setup(self, user_id: str) -> str:
        """Start account setup process"""
        self.pending_setups[user_id] = {
            'step': 'broker',
            'data': {}
        }
        
        return """
<b>🏦 ADD MT5 ACCOUNT - STEP 1/6</b>

<b>Select Your Broker:</b>
Please type your broker name.

<b>Popular Brokers:</b>
• Exness
• IC Markets
• Pepperstone
• FTMO
• XM
• HFM (HotForex)
• Fusion Markets
• Other (type your broker name)

<b>Example:</b> <code>Exness</code>

Type your broker name or send /cancel to stop.
"""
    
    def process_input(self, user_id: str, input_text: str) -> tuple:
        """
        Process user input for account setup
        Returns: (completed: bool, message: str, data: dict or None)
        """
        if user_id not in self.pending_setups:
            return False, "No setup in progress. Use /addaccount to start.", None
        
        setup = self.pending_setups[user_id]
        step = setup['step']
        data = setup['data']
        
        # Process based on current step
        if step == 'broker':
            data['broker'] = input_text
            setup['step'] = 'server'
            
            message = f"""
<b>🌐 ADD MT5 ACCOUNT - STEP 2/6</b>

<b>Broker:</b> {data['broker']}

<b>Enter MT5 Server Name:</b>
This is usually shown when you log into MT5.

<b>Examples:</b>
• Exness: <code>Exness-MT5Trial9</code>
• IC Markets: <code>ICMarketsSC-Demo</code>
• FTMO: <code>FTMO-Demo</code>

<b>Where to find it:</b>
Open MT5 → Tools → Options → Server tab

Type the exact server name or /cancel to stop.
"""
            return False, message, None
        
        elif step == 'server':
            data['server'] = input_text
            setup['step'] = 'login'
            
            message = f"""
<b>🔢 ADD MT5 ACCOUNT - STEP 3/6</b>

<b>Broker:</b> {data['broker']}
<b>Server:</b> {data['server']}

<b>Enter Your MT5 Account Number (Login):</b>
This is your account number shown in MT5.

<b>Example:</b> <code>12345678</code>

⚠️ Make sure you enter the correct account number.

Type your account number or /cancel to stop.
"""
            return False, message, None
        
        elif step == 'login':
            # Validate login is numeric
            if not input_text.isdigit():
                return False, "❌ Invalid account number. Please enter numbers only.", None
            
            data['login'] = input_text
            setup['step'] = 'password'
            
            message = f"""
<b>🔐 ADD MT5 ACCOUNT - STEP 4/6</b>

<b>Broker:</b> {data['broker']}
<b>Server:</b> {data['server']}
<b>Login:</b> {data['login']}

<b>Enter Your MT5 Password:</b>
This is the password you use to log into MT5.

🔒 <b>Security Notes:</b>
• Your password is encrypted and stored securely
• Only you can access this account
• Password is never shown in plain text
• You can delete the account anytime

⚠️ <b>IMPORTANT:</b> Make sure you trust this bot before entering your password.

Type your password or /cancel to stop.
"""
            return False, message, None
        
        elif step == 'password':
            data['password'] = input_text
            setup['step'] = 'nickname'
            
            # Don't show password in confirmation
            message = f"""
<b>📝 ADD MT5 ACCOUNT - STEP 5/6</b>

<b>Broker:</b> {data['broker']}
<b>Server:</b> {data['server']}
<b>Login:</b> {data['login']}
<b>Password:</b> ********** (stored securely)

<b>Give This Account a Nickname:</b>
Choose a friendly name to identify this account.

<b>Examples:</b>
• My Demo Account
• Main Trading
• Scalping Account
• FTMO Challenge

Type a nickname (max 30 characters) or /cancel to stop.
"""
            return False, message, None
        
        elif step == 'nickname':
            if len(input_text) > 30:
                return False, "❌ Nickname too long. Please use 30 characters or less.", None
            
            data['nickname'] = input_text
            setup['step'] = 'confirmation'
            
            message = f"""
<b>✅ ADD MT5 ACCOUNT - STEP 6/6 - CONFIRMATION</b>

<b>Please verify your account details:</b>

<b>Nickname:</b> {data['nickname']}
<b>Broker:</b> {data['broker']}
<b>Server:</b> {data['server']}
<b>Login:</b> {data['login']}
<b>Password:</b> **********

<b>Auto-Execution:</b> Will be ENABLED by default
(You can disable it later with /myaccounts)

<b>Commands:</b>
• Type <code>confirm</code> to add this account
• Type <code>cancel</code> to discard and start over

Is everything correct?
"""
            return False, message, None
        
        elif step == 'confirmation':
            if input_text.lower() == 'confirm':
                # Setup complete - return data
                account_data = data.copy()
                del self.pending_setups[user_id]
                return True, "Account setup completed!", account_data
            elif input_text.lower() == 'cancel':
                del self.pending_setups[user_id]
                return True, "Account setup cancelled.", None
            else:
                return False, "Please type 'confirm' or 'cancel'.", None
        
        return False, "Unknown step. Please use /addaccount to start over.", None
    
    def cancel_setup(self, user_id: str):
        """Cancel ongoing setup"""
        if user_id in self.pending_setups:
            del self.pending_setups[user_id]
            return True
        return False
    
    def has_pending_setup(self, user_id: str) -> bool:
        """Check if user has pending setup"""
        return user_id in self.pending_setups