#!/usr/bin/env python3
"""
Final Super Telegram Bot (SQLite Persistence + Reset + Cleanup)
"""

import os
import tempfile
import uuid
from pathlib import Path
from PIL import Image
from rembg import remove
import asyncio
import yt_dlp
import requests
import sqlite3   # cleanup এর জন্য

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    SQLitePersistence,
)

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "123456789:MY_BOT_TOKEN")
MONETAG_LINK = "https://otieu.com/4/9875089"
TMP_DIR = tempfile.gettempdir()
FILEIO_ENDPOINT = "https://file.io"


# ---------------- UTILITIES ----------------
def unique_path(suffix: str):
    return os.path.join(TMP_DIR, f"{uuid.uuid4().hex}{suffix}")


async def run_blocking(func, *args, **kwargs):
    return await asyncio.get_event_loop().run_in_executor(None, lambda: func(*args, **kwargs))


def upload_to_fileio(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            r = requests.post(FILEIO_ENDPOINT, files={"file": f})
        if r.status_code == 200:
            return r.json().get("link")
    except:
        return None
    return None


# ---------------- KEYBOARDS ----------------
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📧 Temp Gmail", callback_data="temp_gmail")],
        [InlineKeyboardButton("📱 Temp Number", callback_data="temp_number")],
        [InlineKeyboardButton("🎥 Video Downloader", callback_data="submenu_video")],
        [InlineKeyboardButton("🖼 Background Tools", callback_data="submenu_bg")],
        [InlineKeyboardButton("📏 Pic Size Converter", callback_data="resize")]
    ])


def bg_tools_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Remove Background", callback_data="removebg")],
        [InlineKeyboardButton("🎨 Change Color", callback_data="bgcolor")],
        [InlineKeyboardButton("🖼 Replace Background", callback_data="bgimage")],
        [InlineKeyboardButton("⬅ Back", callback_data="back_main")]
    ])


def video_tools_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶ YouTube", callback_data="video_youtube")],
        [InlineKeyboardButton("🎶 TikTok", callback_data="video_tiktok")],
        [InlineKeyboardButton("📘 Facebook", callback_data="video_facebook")],
        [InlineKeyboardButton("📸 Instagram", callback_data="video_instagram")],
        [InlineKeyboardButton("⬅ Back", callback_data="back_main")]
    ])


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Super Bot!\nChoose an option:",
        reply_markup=main_menu_keyboard()
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Monetag auto call (hidden hit)
    try:
        requests.get(MONETAG_LINK, timeout=3)
    except:
        pass

    if query.data == "submenu_bg":
        await query.edit_message_text("🖼 Background Tools:", reply_markup=bg_tools_keyboard())

    elif query.data == "submenu_video":
        await query.edit_message_text("🎥 Video Downloader:", reply_markup=video_tools_keyboard())

    elif query.data == "back_main":
        await query.edit_message_text("👋 Back to Main Menu:", reply_markup=main_menu_keyboard())

    elif query.data == "temp_gmail":
        await query.message.reply_text("📧 Fetching Temp Gmail...")
        await query.message.reply_text("✅ Your Temp Gmail: `user123@tempmail.com`", parse_mode="Markdown")

    elif query.data == "temp_number":
        await query.message.reply_text("📱 Fetching Temp Number...")
        await query.message.reply_text("✅ Your Temp Number: `+1234567890`", parse_mode="Markdown")

    elif query.data == "removebg":
        context.user_data["action"] = "removebg"
        await query.message.reply_text("📸 Send me a photo to remove background.")

    elif query.data == "bgcolor":
        context.user_data["action"] = "bgcolor"
        context.user_data["bgcolor"] = "#00FF00"
        await query.message.reply_text("🎨 Send a photo, I will change its background color.")

    elif query.data == "bgimage":
        context.user_data["action"] = "await_bgimage"
        await query.message.reply_text("🖼 Send me the background image first.")

    elif query.data == "resize":
        context.user_data["action"] = "resize"
        context.user_data["resize"] = (512, 512)
        await query.message.reply_text("📏 Send a photo, I will resize to 512x512. Use /resize W H to set size.")

    elif query.data.startswith("video_"):
        platform = query.data.split("_")[1]
        context.user_data["action"] = f"video_{platform}"
        await query.message.reply_text(f"🎥 Send me a {platform} video link.")


# ---------------- COMMANDS ----------------
async def resize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /resize WIDTH HEIGHT")
        return
    try:
        w, h = int(context.args[0]), int(context.args[1])
        context.user_data["resize"] = (w, h)
        await update.message.reply_text(f"✅ Resize set to {w}x{h}. Now send a photo.")
    except:
        await update.message.reply_text("⚠️ Invalid format. Example: /resize 800 600")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("♻️ আপনার সব সেটিংস রিসেট করা হয়েছে। আবার /start দিন।")


async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("bot_data.sqlite")
    conn.execute("VACUUM;")
    conn.close()
    await update.message.reply_text("🧹 ডাটাবেজ ক্লিনআপ সম্পন্ন ✅")


# ---------------- PHOTO HANDLER ----------------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("action")

    photo_file = await update.message.photo[-1].get_file()
    local_in = unique_path(".png")
    await photo_file.download_to_drive(local_in)

    try:
        if action == "removebg":
            fg = remove(Image.open(local_in))
            out = unique_path(".png")
            fg.save(out)
            link = upload_to_fileio(out)
            with open(out, "rb") as f:
                await update.message.reply_photo(f, caption=f"✅ Background removed\n📂 {link}")
            os.remove(out)

        elif action == "bgcolor":
            color = context.user_data.get("bgcolor", "#00FF00")
            fg = remove(Image.open(local_in))
            bg = Image.new("RGB", fg.size, color)
            out = unique_path(".png")
            bg.paste(fg, mask=fg.split()[3])
            bg.save(out)
            link = upload_to_fileio(out)
            with open(out, "rb") as f:
                await update.message.reply_photo(f, caption=f"✅ BG set to {color}\n📂 {link}")
            os.remove(out)

        elif action == "await_bgimage":
            bg_path = unique_path(".png")
            Image.open(local_in).save(bg_path)
            context.user_data["bgimage"] = bg_path
            context.user_data["action"] = "bgimage"
            await update.message.reply_text("✅ Background image saved. Now send target photo.")

        elif action == "bgimage":
            bg_path = context.user_data.get("bgimage")
            if not bg_path:
                await update.message.reply_text("⚠️ Please send background image first.")
                return
            fg = remove(Image.open(local_in))
            bg = Image.open(bg_path).resize(fg.size)
            out = unique_path(".png")
            bg.paste(fg, mask=fg.split()[3])
            bg.save(out)
            link = upload_to_fileio(out)
            with open(out, "rb") as f:
                await update.message.reply_photo(f, caption=f"✅ Background replaced\n📂 {link}")
            os.remove(out)

        elif action == "resize":
            w, h = context.user_data.get("resize", (512, 512))
            img = Image.open(local_in)
            out = unique_path(".png")
            img.resize((w, h)).save(out)
            link = upload_to_fileio(out)
            with open(out, "rb") as f:
                await update.message.reply_photo(f, caption=f"✅ Resized to {w}x{h}\n📂 {link}")
            os.remove(out)

        else:
            await update.message.reply_text("⚠️ Please select an option first (/start).")

    finally:
        if os.path.exists(local_in):
            os.remove(local_in)


# ---------------- TEXT HANDLER ----------------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("action")
    text = update.message.text.strip()

    if action and action.startswith("video_") and text.startswith("http"):
        platform = action.split("_")[1]
        await update.message.reply_text(f"⏳ Downloading {platform} video...")

        tmp_file = unique_path(".mp4")
        ydl_opts = {"outtmpl": tmp_file, "format": "best[ext=mp4]/best", "noplaylist": True, "quiet": True}

        ok = True
        try:
            await run_blocking(lambda: yt_dlp.YoutubeDL(ydl_opts).download([text]))
        except Exception as e:
            ok = False
            await update.message.reply_text(f"❌ Download failed: {e}")

        if ok:
            size_mb = Path(tmp_file).stat().st_size / (1024 * 1024)
            if size_mb < 50:
                with open(tmp_file, "rb") as f:
                    await update.message.reply_video(f, caption="✅ Download complete")
            else:
                link = upload_to_fileio(tmp_file)
                if link:
                    await update.message.reply_text(f"📂 File is large. Download: {link}")
                else:
                    await update.message.reply_text("⚠️ Upload failed.")
            os.remove(tmp_file)

    else:
        await update.message.reply_text("⚡ Please use the menu buttons or send a valid link.")


# ---------------- MAIN ----------------
def main():
    persistence = SQLitePersistence("bot_data.sqlite")

    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("resize", resize_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("cleanup", cleanup_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🤖 Bot is running with SQLite persistence...")
    app.run_polling()


if __name__ == "__main__":
    main()
