# NIXIE'S TRADING BOT - Installation Checklist

**Complete this checklist to ensure proper installation**

---

## Pre-Installation Requirements

### System Requirements
- [ ] Windows 10 or later (64-bit)
- [ ] 4GB RAM minimum (8GB recommended)
- [ ] 1GB free disk space
- [ ] Stable internet connection
- [ ] Administrator access

### Software Requirements
- [ ] Python 3.9+ installed
- [ ] Python added to PATH
- [ ] MetaTrader 5 installed
- [ ] Telegram app on phone
- [ ] Text editor (Notepad++ or VS Code)

### Account Requirements
- [ ] Exness trading account created
- [ ] MT5 account credentials available
- [ ] Telegram account active
- [ ] Telegram bot created (via BotFather)
- [ ] Telegram User ID obtained

---

## Installation Steps

### Step 1: Python Installation
- [ ] Downloaded Python from python.org
- [ ] Ran installer
- [ ] **CHECKED "Add Python to PATH"** ✅
- [ ] Completed installation
- [ ] Verified: `python --version` shows version
- [ ] Verified: `pip --version` shows version

**Verification Command:**
```bash
python --version
# Should show: Python 3.9.x or higher
```

---

### Step 2: MetaTrader 5 Setup
- [ ] Downloaded MT5 from Exness
- [ ] Installed MT5 terminal
- [ ] Logged into trading account
- [ ] Verified account is active
- [ ] Enabled Algo Trading:
  - [ ] Tools → Options
  - [ ] Expert Advisors tab
  - [ ] ✅ Allow automated trading
  - [ ] ✅ Allow DLL imports
- [ ] Clicked OK

**Verification:**
- [ ] MT5 shows "Connected" in bottom right
- [ ] Can see live price quotes
- [ ] Account balance displays correctly

---

### Step 3: Telegram Bot Creation
- [ ] Opened Telegram app
- [ ] Searched for `@BotFather`
- [ ] Sent `/newbot` command
- [ ] Provided bot name: `Nixie Trading Bot`
- [ ] Provided username: `nixie_trading_bot` (or unique)
- [ ] **COPIED bot token** (format: 123456789:ABC...)
- [ ] Saved token in secure location

**Get Your Telegram ID:**
- [ ] Searched for `@userinfobot`
- [ ] Sent `/start` command
- [ ] **COPIED your user ID** (number like 987654321)
- [ ] Saved ID in secure location

**Verification:**
- [ ] Bot appears in your contacts
- [ ] Bot responds when you send `/start`
- [ ] You have both token and ID saved

---

### Step 4: Project Download
- [ ] Went to GitHub repository
- [ ] Clicked green "Code" button
- [ ] Downloaded ZIP file
- [ ] Extracted to Desktop
- [ ] Renamed folder to `nixie-trading-bot`
- [ ] Can see all files inside folder

**Verification:**
```bash
cd Desktop\nixie-trading-bot
dir
# Should see: main.py, requirements.txt, src/, etc.
```

---

### Step 5: Virtual Environment
- [ ] Opened Command Prompt
- [ ] Navigated to project folder
- [ ] Created virtual environment: `python -m venv venv`
- [ ] Waited for completion (1-2 minutes)
- [ ] Verified `venv` folder exists

**Activation:**
- [ ] Windows: `venv\Scripts\activate`
- [ ] Saw `(venv)` appear in prompt

**Verification:**
```bash
where python
# Should show path inside venv folder
```

---

### Step 6: Dependencies Installation
- [ ] Virtual environment is activated `(venv)`
- [ ] Ran: `pip install -r requirements.txt`
- [ ] Waited for installation (3-5 minutes)
- [ ] No major errors appeared
- [ ] All packages installed successfully

**Verification:**
```bash
pip list
# Should show: MetaTrader5, pandas, telegram, etc.
```

**Common Packages to Verify:**
- [ ] MetaTrader5
- [ ] python-telegram-bot
- [ ] pandas
- [ ] numpy
- [ ] scikit-learn
- [ ] colorama
- [ ] pyfiglet
- [ ] aiosqlite

---

### Step 7: Configuration File
- [ ] Found `.env.template` file
- [ ] Copied it and renamed to `.env`
- [ ] Opened `.env` with text editor

**Filled in these fields:**
- [ ] `MT5_LOGIN=` (your account number)
- [ ] `MT5_PASSWORD=` (your password)
- [ ] `MT5_SERVER=` (usually Exness-MT5Trial7)
- [ ] `TELEGRAM_BOT_TOKEN=` (from BotFather)
- [ ] `TELEGRAM_ADMIN_ID=` (from userinfobot)

**Verification:**
- [ ] No quotes around values
- [ ] No extra spaces
- [ ] No `your_` placeholder text remaining
- [ ] File saved as `.env` (not `.env.template`)

**Example correct format:**
```
MT5_LOGIN=12345678
MT5_PASSWORD=MySecretPass123
MT5_SERVER=Exness-MT5Trial7
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrs
TELEGRAM_ADMIN_ID=987654321
```

---

### Step 8: Directory Structure
- [ ] `data/` folder exists or will be created
- [ ] `logs/` folder exists or will be created
- [ ] `models/` folder exists or will be created
- [ ] All Python files in `src/` folder

**Manual Creation (if needed):**
```bash
mkdir data
mkdir logs
mkdir models
```

---

### Step 9: First Run Test
- [ ] MT5 is open and logged in
- [ ] Virtual environment is activated
- [ ] In project directory

**Start the bot:**
```bash
python main.py
```

**Expected Output:**
- [ ] Saw animated NIXIE'S TRADING BOT banner
- [ ] Saw colorful initialization messages
- [ ] Saw: `[MT5] Connected successfully` ✅
- [ ] Saw: `[ANALYZER] Market analyzer ready` ✅
- [ ] Saw: `[ML] Machine learning engine loaded` ✅
- [ ] Saw: `[TELEGRAM] Telegram bot started` ✅
- [ ] Saw: `[SYSTEM] All systems operational` ✅
- [ ] Saw: `[SCAN] Market scan started` message

**Telegram Verification:**
- [ ] Received Telegram message from bot
- [ ] Message says "SYSTEM ONLINE"
- [ ] Message shows current date/time

**If All Green ✅:**
🎉 **BOT IS RUNNING SUCCESSFULLY!** 🎉

---

### Step 10: User Interaction Test
**In Telegram, test these commands:**

- [ ] `/start` - Received welcome message
- [ ] `/subscribe` - Subscription activated
- [ ] `/status` - Shows "ACTIVE"
- [ ] `/stats` - Shows bot statistics
- [ ] `/help` - Shows help information

**Verification:**
- [ ] All commands respond
- [ ] Messages are formatted correctly
- [ ] No error messages

---

## Post-Installation Verification

### System Health Check
- [ ] Bot running without errors
- [ ] No red error messages in console
- [ ] Log file created: `logs/nixie_bot.log`
- [ ] Database created: `data/trading_data.db`

**Check Log File:**
```bash
type logs\nixie_bot.log
# Should see initialization logs, no errors
```

### Performance Check
- [ ] CPU usage normal (<10%)
- [ ] Memory usage normal (<200MB)
- [ ] No crashes or freezes
- [ ] Market scans completing every 5 minutes

**Watch Console Output:**
- Look for: `[SCAN] Market scan started`
- Should appear every 5 minutes
- No error messages

### Connectivity Check
- [ ] MT5 connected (green in MT5 terminal)
- [ ] Telegram bot responsive
- [ ] Internet connection stable
- [ ] No firewall blocking

---

## Troubleshooting Checklist

### If "MT5 initialization failed"
- [ ] MT5 terminal is open
- [ ] MT5 shows "Connected"
- [ ] Account credentials correct in `.env`
- [ ] Server name correct (check in MT5)
- [ ] Algo Trading enabled in MT5
- [ ] Restarted MT5 terminal

### If "Telegram bot not responding"
- [ ] Bot token correct in `.env`
- [ ] No extra spaces in token
- [ ] Internet connection working
- [ ] Telegram app is open
- [ ] Bot not deleted/blocked
- [ ] Tried `/start` command

### If "Python not found"
- [ ] Python installed correctly
- [ ] Added to PATH during installation
- [ ] Restarted Command Prompt
- [ ] Restarted computer
- [ ] Reinstalled Python

### If "Module not found"
- [ ] Virtual environment activated
- [ ] Ran `pip install -r requirements.txt`
- [ ] No errors during installation
- [ ] Check `pip list` output
- [ ] Try reinstalling: `pip install --upgrade -r requirements.txt`

### If "No signals generated"
- [ ] This is NORMAL - signals are rare
- [ ] Bot is working correctly
- [ ] Wait for market conditions to align
- [ ] Check it's within kill zone hours (8-17 UTC)
- [ ] Markets must be open
- [ ] Be patient (2-5 signals/day typical)

---

## Security Verification

### File Security
- [ ] `.env` file exists
- [ ] `.env` NOT in Git repository
- [ ] `.gitignore` includes `.env`
- [ ] Credentials not shared

### Permission Security
- [ ] Only you have access to `.env`
- [ ] Files not in public folders
- [ ] Telegram admin ID is yours
- [ ] MT5 password is strong

---

## Optional Advanced Setup

### VPS Deployment
- [ ] VPS purchased and set up
- [ ] RDP connection working
- [ ] Bot installed on VPS
- [ ] Auto-start configured
- [ ] Monitored remotely

### Backup Setup
- [ ] Backup script created
- [ ] Daily backup scheduled
- [ ] `.env` file backed up securely
- [ ] Database backed up
- [ ] Models folder backed up

### Monitoring Setup
- [ ] Log monitoring configured
- [ ] Alert system set up
- [ ] Performance tracking enabled
- [ ] Remote access configured

---

## Final Verification

### Complete Installation Checklist
**Count your checks - should have 100+ boxes checked!**

- [ ] All prerequisites met
- [ ] All installation steps completed
- [ ] All verifications passed
- [ ] Bot running successfully
- [ ] Telegram commands working
- [ ] No errors in logs
- [ ] Security measures in place

### Success Criteria
✅ Bot starts without errors  
✅ MT5 connection active  
✅ Telegram bot responsive  
✅ Market scans every 5 minutes  
✅ Logs being written  
✅ Database created  
✅ Can subscribe/unsubscribe  

**If all criteria met:**
# 🎉 INSTALLATION SUCCESSFUL! 🎉

---

## Next Steps

### After Installation
1. **Let it run** - Leave bot running for 24 hours
2. **Monitor** - Check logs regularly
3. **Test signals** - Wait for first signal
4. **Verify quality** - Check signal format
5. **Demo trade** - Test signals on demo account

### First Week Tasks
- [ ] Monitor daily performance
- [ ] Review generated signals
- [ ] Check ML confidence scores
- [ ] Verify signal quality
- [ ] Test signal execution
- [ ] Keep logs for review

### First Month Tasks
- [ ] Analyze win rate
- [ ] Review ML training
- [ ] Optimize settings if needed
- [ ] Scale to live account (if demo successful)
- [ ] Join community discussions
- [ ] Provide feedback

---

## Support Resources

### If You Need Help
1. **Read Documentation:**
   - [ ] README.md
   - [ ] IMPLEMENTATION_GUIDE.md
   - [ ] QUICKSTART.md
   - [ ] PROJECT_STRUCTURE.md

2. **Check Logs:**
   - [ ] `logs/nixie_bot.log`
   - [ ] Look for error messages
   - [ ] Note timestamps of issues

3. **Verify Setup:**
   - [ ] Review this checklist
   - [ ] Ensure all boxes checked
   - [ ] Double-check configuration

4. **Get Help:**
   - [ ] Search GitHub Issues
   - [ ] Create new Issue with details
   - [ ] Include log excerpts
   - [ ] Describe problem clearly

---

## Maintenance Schedule

### Daily
- [ ] Check bot status
- [ ] Review any signals
- [ ] Check logs for errors

### Weekly
- [ ] Review signal quality
- [ ] Check ML performance
- [ ] Backup database
- [ ] Update outcomes

### Monthly
- [ ] Review overall performance
- [ ] Update dependencies
- [ ] Clean old logs
- [ ] Optimize settings

---

## Emergency Procedures

### If Bot Crashes
1. [ ] Check logs for error
2. [ ] Verify MT5 connection
3. [ ] Restart bot
4. [ ] Monitor for repeat
5. [ ] Report issue if persists

### If Losing Connection
1. [ ] Check internet
2. [ ] Check MT5 status
3. [ ] Verify credentials
4. [ ] Restart MT5
5. [ ] Restart bot

### If Signals Seem Wrong
1. [ ] **STOP TRADING**
2. [ ] Review signal details
3. [ ] Check market conditions
4. [ ] Verify strategy logic
5. [ ] Test on demo only

---

## Congratulations!

**You've successfully installed Nixie's Trading Bot!**

Your bot is now:
- 🔍 Scanning 23 markets
- 🧠 Analyzing with AI
- 📊 Identifying high-probability setups
- 📱 Ready to send signals
- 📈 Learning and improving

**Remember:**
- Be patient (quality > quantity)
- Start with demo account
- Follow risk management (2% max)
- Never risk more than you can afford
- Review signals before trading

**Good luck with your trading journey!** 🚀💰

---

**Author:** Blessing Omoregie (Nixiestone)  
**Support:** GitHub Issues  
**Documentation:** All .md files in project

**Built with precision. Trades with confidence.**

---

**INSTALLATION COMPLETE** ✅