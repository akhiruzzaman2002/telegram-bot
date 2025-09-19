#!/bin/bash
echo "🚀 Installing dependencies..."
pip install -r requirements.txt

if [ -z "$1" ]; then
  echo "⚠️ Usage: bash start.sh <lite_bot.py|full_bot.py>"
  exit 1
fi

echo "🤖 Starting $1 ..."
python $1
