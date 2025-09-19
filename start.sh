#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting bot..."
python super_bot.py
