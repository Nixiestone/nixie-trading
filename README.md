# NIXIE'S TRADING BOT

**High-Precision Institutional SMC Trading Bot with ML Integration**

Author: Blessing Omoregie (Nixiestone)  
GitHub: [@Nixiestone](https://github.com/Nixiestone)

---

## Overview

Nixie's Trading Bot is an advanced, AI-powered trading system that implements Smart Money Concepts (SMC) strategy to analyze Forex pairs, Metals (Gold, Silver), and Indices. The bot uses institutional precision scalping techniques combined with machine learning to identify high-probability trading opportunities with a minimum 1:3 Risk:Reward ratio.

### Key Features

- **Smart Money Concepts (SMC)** implementation
- **Multi-timeframe analysis** (H4, H1, M5, M1)
- **Machine Learning** enhanced signal quality prediction
- **Automatic training** after every 20 signals
- **Telegram integration** with multi-user support
- **Real-time market scanning** every 5 minutes
- **Hourly market updates** when no signals are generated
- **65%+ target win rate** based on institutional strategies
- **Minimum 1:3 Risk:Reward** on all signals

---

## Strategy Overview

The bot implements the institutional precision scalping strategy focusing on:

1. **Liquidity Sweep Detection** - Identifies stop-loss hunts
2. **Market Structure Breaks** - Confirms directional bias
3. **Fair Value Gaps (FVG)** - Identifies price inefficiencies
4. **Order Blocks (OB)** - Locates institutional entry zones
5. **Displacement Moves** - Confirms smart money commitment
6. **Kill Zone Trading** - Operates during London & NY sessions

---

## Installation Guide

### Prerequisites

- Python 3.9 or higher
- MetaTrader 5 terminal installed
- Exness trading account (or compatible MT5 broker)
- Telegram account
- Windows OS (for MT5 integration)

### Step 1: Clone Repository

```bash
git clone https://github.com/Nixiestone/nixie-trading.git
cd nixie-trading-bot
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
```

### Step 3: Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Set Up MetaTrader 5

1. Install MetaTrader 5 from Exness
2. Log into your trading account
3. Enable **Algo Trading** in MT5:
   - Tools → Options → Expert Advisors
   - Check "Allow automated trading"
   - Check "Allow DLL imports"

### Step 6: Create Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the **bot token** provided
5. Get your **Telegram User ID**:
   - Search for **@userinfobot**
   - Send `/start`
   - Copy your user ID

### Step 7: Configure Environment Variables

1. Copy `.env.template` to `.env`:
   ```bash
   copy .env.template .env
   ```

2. Edit `.env` file with your credentials:
   ```
   MT5_LOGIN=12345678
   MT5_PASSWORD=YourPassword123
   MT5_SERVER=Exness-MT5Trial9
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_ADMIN_ID=987654321
   ```

---

## Running the Bot

### Start the Bot

```bash
python main.py
```

You should see the animated NIXIE'S TRADING BOT banner and initialization messages.

### Stop the Bot

Press `Ctrl + C` to gracefully shutdown the bot.

---

## Telegram Bot Commands

Once the bot is running, users can interact via Telegram:

### User Commands

- `/start` - Welcome message and bot overview
- `/subscribe` - Subscribe to trading signals
- `/unsubscribe` - Unsubscribe from signals
- `/status` - Check subscription status
- `/stats` - View bot performance statistics
- `/help` - Show help information

---

## Signal Format

Each signal sent includes:

```
NEW TRADING SIGNAL

Symbol: XAUUSD
Direction: BUY
Signal Strength: HIGH

ENTRY DETAILS:
Entry Type: LIMIT
Entry Price: 2650.50

RISK MANAGEMENT:
Stop Loss: 2645.00 (55.0 pips)
Take Profit: 2665.00 (145.0 pips)
Risk:Reward: 1:2.64

TECHNICAL DATA:
Setup: FVG_OB_CONFLUENCE
ML Confidence: 78.5%
Current Price: 2652.30
ATR: 12.50
RSI: 58.3

MARKET CONDITIONS:
Trend: STRONG_BULLISH
Bias: BULLISH
Volatility: MEDIUM

Time Generated: 2024-12-07 14:30:45 UTC
```

---

## Project Structure

```
nixie-trading-bot/
│
├── main.py                      # Main entry point
├── requirements.txt             # Python dependencies
├── .env.template               # Environment variables template
├── README.md                   # This file
├── IMPLEMENTATION_GUIDE.md     # 5-year-old friendly guide
│
├── src/
│   ├── config/
│   │   └── settings.py         # Configuration settings
│   │
│   ├── core/
│   │   ├── market_analyzer.py  # Market analysis engine
│   │   ├── signal_generator.py # Signal generation
│   │   └── ml_engine.py        # Machine learning engine
│   │
│   ├── mt5/
│   │   └── connection.py       # MT5 connection handler
│   │
│   ├── telegram/
│   │   └── bot_handler.py      # Telegram bot handler
│   │
│   └── utils/
│       ├── logger.py           # Logging utility
│       └── database.py         # Database handler
│
├── data/                       # Database files
├── logs/                       # Log files
└── models/                     # ML models
```

---

## How It Works

### 1. Market Scanning (Every 5 Minutes)

The bot scans all configured symbols analyzing:
- Higher timeframe trend (H4)
- Market structure (BOS/ChoCH)
- Liquidity zones (PDH/PDL)
- Fair Value Gaps
- Order Blocks

### 2. Signal Generation

When all conditions align:
- Liquidity sweep detected
- Displacement move confirmed
- FVG or OB present
- Within kill zone hours
- ML confidence > 60%

A signal is generated and broadcast to subscribers.

### 3. Machine Learning Training

- After every 20 signals, the ML model automatically trains
- Learns from signal outcomes (wins/losses)
- Improves confidence predictions over time
- Adapts to changing market conditions

### 4. Hourly Updates

If no signals are generated in an hour, subscribers receive:
- Current market conditions
- Price levels for all symbols
- Trend and volatility status
- Market bias

---

## Risk Management

The bot follows strict institutional risk management:

1. **2% Maximum Risk Per Trade** (Non-negotiable)
2. **Minimum 1:3 Risk:Reward Ratio**
3. **Maximum 4% Daily Drawdown**
4. **Maximum 8% Weekly Drawdown**
5. **65%+ Target Win Rate**

### Position Sizing

Position sizes are calculated automatically to risk exactly 2% per trade based on:
- Account balance
- Stop loss distance
- Symbol pip value

---

## Performance Monitoring

### View Statistics

Users can check bot performance anytime:

```
/stats command shows:
- Total signals generated
- Win rate percentage
- Average Risk:Reward
- ML model training status
- Active subscribers
```

### Logs

All activities are logged in `logs/nixie_bot.log`:
- Market analysis results
- Signal generation details
- ML training progress
- User subscriptions
- Errors and warnings

---

## Customization

### Adding More Symbols

Edit `src/config/settings.py`:

```python
TRADING_SYMBOLS = [
    'EURUSD', 'GBPUSD', 'USDJPY',  # Add more forex pairs
    'XAUUSD', 'XAGUSD',             # Add more metals
    'US30', 'US100', 'US500'        # Add more indices
]
```

### Adjusting Parameters

Modify strategy parameters in `settings.py`:

```python
MAX_RISK_PERCENT = 2.0      # Risk per trade
MIN_RISK_REWARD = 3.0       # Minimum R:R
FVG_MIN_SIZE = 5            # FVG threshold
DISPLACEMENT_MIN_SIZE = 15  # Displacement threshold
```

---

## Troubleshooting

### MT5 Connection Failed

1. Ensure MT5 terminal is running
2. Check account credentials in `.env`
3. Verify server name (Exness-MT5Trial9)
4. Enable Algo Trading in MT5

### Telegram Bot Not Responding

1. Verify bot token in `.env`
2. Check internet connection
3. Ensure bot is not stopped by Telegram
4. Review logs for errors

### No Signals Generated

1. Normal - high-quality signals are rare
2. Check if within kill zone hours (London/NY sessions)
3. Verify markets are open
4. Review market conditions (need alignment)

### ML Model Not Training

1. Need at least 20 signals with outcomes
2. Check database for stored signals
3. Review logs for training errors
4. Ensure sufficient disk space

---

## Best Practices

1. **Run on VPS** - Ensures 24/7 operation and low latency
2. **Start with Demo Account** - Test thoroughly before live trading
3. **Monitor Regularly** - Check logs and statistics
4. **Follow Signals Strictly** - Don't modify R:R ratios
5. **Respect Risk Management** - Never exceed 2% risk per trade
6. **Trade Kill Zones Only** - London and NY sessions
7. **Review ML Performance** - After each training cycle
8. **Keep Software Updated** - Pull latest updates regularly

---

## Advanced Features

### Kill Zone Trading

Bot operates during high-liquidity periods:
- **London Session:** 08:00 - 12:00 UTC
- **New York Session:** 13:00 - 17:00 UTC
- **Overlap (Best):** 13:00 - 12:00 UTC

### Multi-Timeframe Analysis

- **H4:** Trend direction and structure
- **H1:** Intermediate confirmation
- **M5:** Setup identification
- **M1:** Precision entry timing

### Signal Strength Levels

- **VERY_HIGH:** 80+ score (All factors aligned)
- **HIGH:** 65-79 score (Strong setup)
- **MEDIUM:** 50-64 score (Good setup)
- **LOW:** <50 score (Filtered out)

---

## Support & Contribution

### Issues

Found a bug or have a suggestion?
1. Check existing [Issues](https://github.com/Nixiestone/nixie-trading-bot/issues)
2. Create a new issue with details
3. Include logs if reporting a bug

### Contributing

Contributions welcome:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

### Contact

- **Author:** Blessing Omoregie
- **GitHub:** [@Nixiestone](https://github.com/Nixiestone)
- **Email:** [Contact via GitHub]

---

## Disclaimer

**IMPORTANT:** This trading bot is for educational and research purposes only. Trading forex, metals, and indices carries substantial risk of loss. Past performance does not guarantee future results.

- **Never trade with money you cannot afford to lose**
- **Always use proper risk management**
- **Start with a demo account**
- **Understand the strategy before using**
- **The author is not responsible for any trading losses**

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

- Smart Money Concepts methodology
- Institutional trading principles
- MetaTrader 5 platform
- Telegram Bot API
- scikit-learn ML library

---

## Version History

**v1.0.0** (December 2024)
- Initial release
- SMC strategy implementation
- ML integration
- Telegram bot
- Multi-symbol support

---

**Built with precision. Trades with confidence. Powered by institutional wisdom.**

NIXIE'S TRADING BOT - Where AI Meets Smart Money