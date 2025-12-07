"""
Configuration Settings for Nixie's Trading Bot
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration"""
    
    # MT5 Configuration (Exness Broker)
    MT5_LOGIN = int(os.getenv('MT5_LOGIN', '0'))
    MT5_PASSWORD = os.getenv('MT5_PASSWORD', '')
    MT5_SERVER = os.getenv('MT5_SERVER', 'Exness-MT5Trial9')  # Exness server
    MT5_TIMEOUT = int(os.getenv('MT5_TIMEOUT', '60000'))
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_ADMIN_ID = os.getenv('TELEGRAM_ADMIN_ID', '')
    
    # Trading Symbols (Exness notation)
    TRADING_SYMBOLS = [
        # Forex Majors
        'EURUSDm', 'GBPUSDm', 'USDJPYm', 'USDCHFm', 'AUDUSDm', 'USDCADm', 'NZDUSDm',
        # Forex Crosses
        'EURJPYm', 'GBPJPYm', 'EURGBPm', 'EURAUDm', 'EURCADm', 'GBPAUDm', 'GBPCADm',
        # Metals
        'XAUUSDm', 'XAGUSDm',  # Gold and Silver
        # Indices
        'US30m', 'USTECm', 'US500m', 'UK100m', 'DE30m'
        #Crypto
        'BTCUSDm'
    ]
    
    # Risk Management (based on document requirements)
    MAX_RISK_PERCENT = 2.0  # 2% per trade (non-negotiable)
    MIN_RISK_REWARD = 3.0  # Minimum 1:3 R:R
    TARGET_WIN_RATE = 65.0  # Target win rate percentage
    MAX_DAILY_DRAWDOWN = 4.0  # Maximum daily drawdown %
    MAX_WEEKLY_DRAWDOWN = 8.0  # Maximum weekly drawdown %
    
    # Strategy Parameters (SMC)
    TIMEFRAMES = {
        'HTF': '240',  # H4 for higher timeframe analysis
        'MTF': '60',   # H1 for intermediate
        'LTF_ENTRY': '5',   # M5 for entry confirmation
        'LTF_PRECISION': '1'  # M1 for precision entry
    }
    
    # Kill Zones (UTC time)
    LONDON_SESSION = {'start': '08:00', 'end': '12:00'}
    NY_SESSION = {'start': '13:00', 'end': '17:00'}
    LONDON_NY_OVERLAP = {'start': '13:00', 'end': '12:00'}
    
    # Technical Parameters
    FVG_MIN_SIZE = 5  # Minimum FVG size in pips
    OB_LOOKBACK = 20  # Candles to look back for Order Blocks
    LIQUIDITY_THRESHOLD = 10  # Minimum pip distance for liquidity levels
    DISPLACEMENT_MIN_SIZE = 15  # Minimum displacement in pips
    
    # ML Configuration
    ML_TRAINING_THRESHOLD = 20  # Train after this many signals
    ML_MODEL_PATH = 'models/ml_model.pkl'
    ML_SCALER_PATH = 'models/scaler.pkl'
    ML_FEATURES = [
        'volatility', 'atr', 'rsi', 'trend_strength',
        'volume_ratio', 'fvg_size', 'ob_strength',
        'displacement_size', 'liquidity_distance',
        'time_of_day', 'day_of_week'
    ]
    
    # Database
    DB_PATH = 'data/trading_data.db'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/nixie_bot.log'
    
    # Performance Targets (from document)
    WEEKLY_TARGET_RETURN = 30.0  # 30% weekly target
    MAX_SPREAD_COST = 0.5  # Maximum acceptable spread in pips
    
    # Notification Settings
    HOURLY_UPDATE_ENABLED = True
    SIGNAL_COOLDOWN = 300  # 5 minutes between signals for same symbol
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        required = [
            ('MT5_LOGIN', cls.MT5_LOGIN),
            ('MT5_PASSWORD', cls.MT5_PASSWORD),
            ('TELEGRAM_BOT_TOKEN', cls.TELEGRAM_BOT_TOKEN)
        ]
        
        missing = [name for name, value in required if not value or value == '0']
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True
    
    @classmethod
    def get_symbol_info(cls, symbol):
        """Get symbol-specific information for Exness"""
        # Exness-specific symbol configurations
        symbol_configs = {
            'XAUUSDm': {
                'point_value': 0.01,
                'typical_spread': 0.2,
                'margin_required': 100,
                'pip_position': -1
            },
            'XAGUSDm': {
                'point_value': 0.001,
                'typical_spread': 0.03,
                'margin_required': 100,
                'pip_position': -2
            },
            'EURUSDm': {
                'point_value': 0.0001,
                'typical_spread': 0.6,
                'margin_required': 100,
                'pip_position': -4
            }
        }
        
        # Default configuration for symbols not explicitly defined
        default_config = {
            'point_value': 0.0001,
            'typical_spread': 1.0,
            'margin_required': 100,
            'pip_position': -4
        }
        
        return symbol_configs.get(symbol, default_config)