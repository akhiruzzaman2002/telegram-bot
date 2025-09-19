#!/usr/bin/env python3
"""
Super Telegram Bot (Advanced + All Features)
"""

import os
import tempfile
import uuid
from pathlib import Path
from PIL import Image
from rembg import remove
import asyncio
import yt_dlp

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
)

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "123456789:MY_BOT_TOKEN")
MONETAG_LINK = "https://otieu.com/4/9875089"

TMP_DIR = tempfile.gettempdir()

# ---------------- STATE ----------------
USER_ACTION = {}        # user_id -> action
USER_BGCOLOR = {}       # user_id -> color
USER_BGIMAGE = {}       # user_id -> bg path
USER_RESIZE = {}        # user_id -> (w,h)


# ---------------- UTILITIES ----------------
def unique_path(suffix: str):
    return os.path.join(TMP_DIR, f"{uuid.uuid4().hex}{suffix}")


async def run_blocking(func, *args, **kwargs):
    return await asyncio.get_event_loop().run_in_executor(None, lambda: func(*args, **kwargs))


# ---------------- KEYBOARDS ----------------
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📧 Temp Mail", url=MONETAG_LINK)],
        [InlineKeyboardButton("📱 Temp Number", url=MONETAG_LINK)],
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
        "👋 Welcome to Advanced Bot!\nChoose an option:",
        reply_markup=main_menu_keyboard()
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "submenu_bg":
        await query.edit_message_text("🖼 Background Tools:", reply_markup=bg_tools_keyboard())

    elif query.data == "submenu_video":
        await query.edit_message_text("🎥 Video Downloader:", reply_markup=video_tools_keyboard())

    elif query.data == "back_main":
        await query.edit_message_text("👋 Back to Main Menu:", reply_markup=main_menu_keyboard())

    elif query.data == "removebg":
        USER_ACTION[user_id] = "removebg"
        await query.message.reply_text("📸 Send me a photo to remove background.")

    elif query.data == "bgcolor":
        USER_ACTION[user_id] = "bgcolor"
        USER_BGCOLOR[user_id] = "#00FF00"  # default green
        await query.message.reply_text("🎨 Send a photo, I will change its background color.")

    elif query.data == "bgimage":
        USER_ACTION[user_id] = "await_bgimage"
        await query.message.reply_text("🖼 Send me the background image first.")

    elif query.data == "resize":
        USER_ACTION[user_id] = "resize"
        USER_RESIZE[user_id] = (512, 512)  # default
        await query.message.reply_text("📏 Send a photo, I will resize to 512x512. Use /resize W H to set size.")

    elif query.data.startswith("video_"):
        platform = query.data.split("_")[1]
        USER_ACTION[user_id] = f"video_{platform}"
        await query.message.reply_text(f"🎥 Send me a {platform} video link.")


# ---------------- COMMANDS ----------------
async def resize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /resize WIDTH HEIGHT")
        return
    try:
        w, h = int(context.args[0]), int(context.args[1])
        USER_RESIZE[user_id] = (w, h)
        await update.message.reply_text(f"✅ Resize set to {w}x{h}. Now send a photo.")
    except Exception:
        await update.message.reply_text("⚠️ Invalid format. Example: /resize 800 600")


# ---------------- PHOTO HANDLER ----------------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    action = USER_ACTION.get(user_id)

    photo_file = await update.message.photo[-1].get_file()
    local_in = unique_path(".png")
    await photo_file.download_to_drive(local_in)

    try:
        if action == "removebg":
            fg = remove(Image.open(local_in))
            out = unique_path(".png")
            fg.save(out)
            with open(out, "rb") as f:
                await update.message.reply_photo(f, caption="✅ Background removed!")
            os.remove(out)

        elif action == "bgcolor":
            color = USER_BGCOLOR.get(user_id, "#00FF00")
            fg = remove(Image.open(local_in))
            bg = Image.new("RGB", fg.size, color)
            out = unique_path(".png")
            bg.paste(fg, mask=fg.split()[3])
            bg.save(out)
            with open(out, "rb") as f:
                await update.message.reply_photo(f, caption=f"✅ Background set to {color}")
            os.remove(out)

        elif action == "await_bgimage":
            bg_path = unique_path(".png")
            Image.open(local_in).save(bg_path)
            USER_BGIMAGE[user_id] = bg_path
            USER_ACTION[user_id] = "bgimage"
            await update.message.reply_text("✅ Background image saved. Now send target photo.")

        elif action == "bgimage":
            bg_path = USER_BGIMAGE.get(user_id)
            if not bg_path:
                await update.message.reply_text("⚠️ Please send background image first.")
                return
            fg = remove(Image.open(local_in))
            bg = Image.open(bg_path).resize(fg.size)
            out = unique_path(".png")
            bg.paste(fg, mask=fg.split()[3])
            bg.save(out)
            with open(out, "rb") as f:
                await update.message.reply_photo(f, caption="✅ Background replaced!")
            os.remove(out)

        elif action == "resize":
            w, h = USER_RESIZE.get(user_id, (512, 512))
            img = Image.open(local_in)
            out = unique_path(".png")
            img.resize((w, h)).save(out)
            with open(out, "rb") as f:
                await update.message.reply_photo(f, caption=f"✅ Resized to {w}x{h}")
            os.remove(out)

        else:
            await update.message.reply_text("⚠️ Please select an option first (/start).")

    finally:
        if os.path.exists(local_in):
            os.remove(local_in)


# ---------------- TEXT HANDLER ----------------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    action = USER_ACTION.get(user_id)
    text = update.message.text.strip()

    if action and action.startswith("video_") and text.startswith("http"):
        platform = action.split("_")[1]
        await update.message.reply_text(f"⏳ Downloading {platform} video...")

        tmp_file = unique_path(".mp4")
        ydl_opts = {
            "outtmpl": tmp_file,
            "format": "best[ext=mp4]/best",
            "noplaylist": True,
            "quiet": True,
        }

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
                await update.message.reply_text("⚠️ File too large to send (>50MB).")
            os.remove(tmp_file)

    else:
        await update.message.reply_text("⚡ Please use the menu buttons or send a valid link.")


# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("resize", resize_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
