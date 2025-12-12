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
    MT5_SERVER = os.getenv('MT5_SERVER', 'Exness-MT5Trial9')
    MT5_TIMEOUT = int(os.getenv('MT5_TIMEOUT', '60000'))
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_ADMIN_ID = os.getenv('TELEGRAM_ADMIN_ID', '')
    
    # AUTO-EXECUTION TOGGLE
    AUTO_EXECUTE_TRADES = os.getenv('AUTO_EXECUTE_TRADES', 'false').lower() == 'true'
    
    # News Settings (NEW)
    NEWS_SCHEDULE_TIME = "08:00"
    NEWS_REMINDER_MINUTES = 10
    RED_FOLDER_IMPACTS = ["High", "Medium"]
    
    # Trading Control (NEW)
    ALLOW_TRADING_DURING_NEWS = False
    NEWS_BLACKOUT_MINUTES_BEFORE = 15
    NEWS_BLACKOUT_MINUTES_AFTER = 15
    
    # Timezone Settings (NEW)
    DEFAULT_TIMEZONE = "UTC"
    
    # Trading Symbols (Exness notation)
    TRADING_SYMBOLS = [
        # Forex Majors
        'EURUSDm', 'GBPUSDm', 'USDJPYm', 'USDCHFm', 'AUDUSDm', 'USDCADm', 'NZDUSDm',
        # Forex Crosses
        'EURJPYm', 'GBPJPYm', 'EURGBPm', 'EURAUDm', 'EURCADm', 'GBPAUDm', 'GBPCADm',
        # Metals
        'XAUUSDm', 'XAGUSDm',
        # Indices
        'US30m', 'USTECm', 'US500m', 'UK100m', 'DE30m', 'JP225m',
        # Crypto
        'BTCUSDm'
    ]
    
    # Risk Management
    MAX_RISK_PERCENT = 2.0
    MIN_RISK_REWARD = 3.0
    TARGET_WIN_RATE = 65.0
    MAX_DAILY_DRAWDOWN = 4.0
    MAX_WEEKLY_DRAWDOWN = 8.0
    
    # Strategy Parameters (SMC)
    TIMEFRAMES = {
        'HTF': '240',
        'MTF': '60',
        'LTF_ENTRY': '15',
        'LTF_PRECISION': '5'
    }
    
    # Kill Zones (UTC time)
    LONDON_SESSION = {'start': '08:00', 'end': '12:00'}
    NY_SESSION = {'start': '13:00', 'end': '17:00'}
    LONDON_NY_OVERLAP = {'start': '13:00', 'end': '12:00'}
    
    # Technical Parameters
    FVG_MIN_SIZE = 5
    OB_LOOKBACK = 20
    LIQUIDITY_THRESHOLD = 10
    DISPLACEMENT_MIN_SIZE = 15
    
    # ML Configuration
    ML_TRAINING_THRESHOLD = 20
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
    CSV_SIGNALS_PATH = 'data/signals_log.csv'
    CSV_CLOSED_PATH = 'data/closed_trades.csv'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/nixie_bot.log'
    
    # Performance Targets
    WEEKLY_TARGET_RETURN = 30.0
    MAX_SPREAD_COST = 0.5
    
    # Notification Settings
    HOURLY_UPDATE_ENABLED = True
    SIGNAL_COOLDOWN = 300
    
    # Trade Monitoring
    CHECK_TRADES_INTERVAL = 30
    
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
        
        default_config = {
            'point_value': 0.0001,
            'typical_spread': 1.0,
            'margin_required': 100,
            'pip_position': -4
        }
        
        return symbol_configs.get(symbol, default_config)