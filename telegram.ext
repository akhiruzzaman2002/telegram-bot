#!/usr/bin/env python3
"""
Lite Telegram Bot
Features:
 - /start, /help
 - Background Remove (photo)
"""

import os
import tempfile
import uuid
from pathlib import Path
from PIL import Image
from rembg import remove
from dotenv import load_dotenv
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -------- CONFIG --------
load_dotenv()  # local use
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "123456789:MY_BOT_TOKEN")
TMP_DIR = tempfile.gettempdir()
FILEIO_ENDPOINT = "https://file.io"

# -------- UTIL --------
def unique_path(suffix: str):
    return os.path.join(TMP_DIR, f"{uuid.uuid4().hex}{suffix}")

def upload_to_fileio(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            r = requests.post(FILEIO_ENDPOINT, files={"file": f})
        if r.status_code == 200:
            return r.json().get("link")
    except:
        return None
    return None

# -------- COMMANDS --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 হ্যালো! আমি Lite Bot.\n\n"
        "📸 আমাকে একটা ছবি পাঠাও, আমি এর ব্যাকগ্রাউন্ড রিমুভ করে দিবো।\n"
        "ℹ️ হেল্প দেখতে /help লিখো।"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Available Commands:\n"
        "/start - বট চালু করো\n"
        "/help - হেল্প দেখাও\n\n"
        "📸 ছবি পাঠালেই ব্যাকগ্রাউন্ড রিমুভ হবে।"
    )

# -------- PHOTO HANDLER --------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    local_in = unique_path(".png")
    await photo_file.download_to_drive(local_in)

    try:
        fg = remove(Image.open(local_in))
        out = unique_path(".png")
        fg.save(out)

        link = upload_to_fileio(out)
        with open(out, "rb") as f:
            await update.message.reply_photo(f, caption=f"✅ Background Removed\n📂 {link}")
        os.remove(out)

    finally:
        if os.path.exists(local_in):
            os.remove(local_in)

# -------- MAIN --------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("🤖 Lite Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
