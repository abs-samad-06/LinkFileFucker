#!/bin/bash

# Telegram File-to-Link Bot Setup Script
# This script prepares the bot for deployment

set -e

echo "═══════════════════════════════════════════════════════"
echo "  Telegram File-to-Link Bot - Setup Script"
echo "═══════════════════════════════════════════════════════"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate
echo "✓ Virtual environment activated"

# Install dependencies
echo "Installing dependencies..."
pip install --quiet -q -r requirements.txt
echo "✓ Dependencies installed"

# Create data directory
mkdir -p data
echo "✓ Data directory created"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  .env file not found!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Create .env file with the following:"
    echo ""
    cat .env.example
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Get values from:"
    echo "  API_ID, API_HASH: https://my.telegram.org/apps"
    echo "  BOT_TOKEN: Talk to @BotFather"
    echo "  STORAGE_CHANNEL_ID: Create private channel, get ID"
    echo "  ADMIN_ID: Your Telegram user ID"
    echo ""
else
    echo "✓ .env file found"
fi

# Run unit tests
echo ""
echo "Running unit tests..."
python test.py

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Setup Complete! ✓"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your Telegram credentials"
echo "  2. Run: python bot.py"
echo ""
