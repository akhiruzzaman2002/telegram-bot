#!/usr/bin/env python3
"""
Full Super Bot
Features:
 - /start, /help
 - Background remove (photo)
 - YouTube video downloader (yt-dlp)
 - Future expansions possible
"""

import os
import tempfile
import uuid
from pathlib import Path
from PIL import Image
from rembg import remove
from dotenv import load_dotenv
import requests
import yt_dlp

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
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TMP_DIR = tempfile.gettempdir()
FILEIO_ENDPOINT = "https://file.io"

if not BOT_TOKEN:
    raise ValueError("⚠️ TELEGRAM_TOKEN not found in env variables.")

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
        "👋 হ্যালো! আমি Super Bot.\n\n"
        "✅ Available:\n"
        "📸 Send photo → remove background\n"
        "🎥 /yt <url> → download YouTube video\n"
        "ℹ️ /help → get help"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Commands:\n"
        "/start - বট চালু করো\n"
        "/help - হেল্প দেখাও\n"
        "/yt <url> - ইউটিউব ভিডিও নামাও\n\n"
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

# -------- YOUTUBE DOWNLOADER --------
async def yt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ ব্যবহার: /yt <YouTube_URL>")
        return

    url = context.args[0]
    out_file = unique_path(".mp4")

    try:
        ydl_opts = {"outtmpl": out_file, "format": "best"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        with open(out_file, "rb") as f:
            await update.message.reply_video(f, caption="✅ ভিডিও ডাউনলোড সম্পন্ন!")
        os.remove(out_file)

    except Exception as e:
        await update.message.reply_text(f"❌ ভিডিও নামানো যায়নি!\nError: {str(e)}")

# -------- MAIN --------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("yt", yt_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("🤖 Super Bot (Full) is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
