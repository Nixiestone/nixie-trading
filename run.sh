#!/bin/bash

echo "Starting Nixie's Trading Bot..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo ""
fi

# Activate virtual environment
source venv/bin/activate

# Install/Update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.template to .env and configure it."
    echo ""
    exit 1
fi

# Create necessary directories
mkdir -p data logs models

# Run the bot
echo ""
echo "================================"
echo "   STARTING TRADING BOT"
echo "================================"
echo ""
python main.py

# Check exit code
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Bot crashed! Check logs/nixie_bot.log for details."
fi