#!/usr/bin/env python3
"""
Final Super Telegram Bot (Temp Gmail + Temp Number + BG Tools + Video + Resize)
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
import random
import string

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
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "7948273306:AAGY2ri4iKlYxzuVVnKl-5_zXoh7_QKL-fE")  # তোমার BotFather টোকেন এখানে দাও
MONETAG_LINK = "https://otieu.com/4/9875089"
TMP_DIR = tempfile.gettempdir()
FILEIO_ENDPOINT = "https://file.io"

# Temp Number API (Optional Paid)
TEMP_NUMBER_API_KEY = os.getenv("TEMP_NUMBER_API_KEY", "YOUR_5SIM_API_KEY")

# ---------------- STATE ----------------
USER_ACTION = {}
USER_BGCOLOR = {}
USER_BGIMAGE = {}
USER_RESIZE = {}

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


# ---------------- TEMP GMAIL ----------------
def generate_temp_gmail():
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domain = "1secmail.com"
    return f"{username}@{domain}"


def fetch_inbox(email):
    login, domain = email.split("@")
    url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}"
    return requests.get(url).json()


def read_message(email, msg_id):
    login, domain = email.split("@")
    url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}"
    return requests.get(url).json()


# ---------------- TEMP NUMBER ----------------
def generate_fake_temp_number():
    country_code = random.choice(["+1", "+44", "+91", "+880"])
    number = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{country_code}{number}"


def buy_temp_number():
    url = "https://5sim.net/v1/user/buy/activation/any/any/telegram"
    headers = {"Authorization": f"Bearer {TEMP_NUMBER_API_KEY}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        return data["phone"], data["id"]
    else:
        return None, None


def check_sms(order_id):
    url = f"https://5sim.net/v1/user/check/{order_id}"
    headers = {"Authorization": f"Bearer {TEMP_NUMBER_API_KEY}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        if data.get("sms"):
            return data["sms"][0]["code"]
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
    user_id = query.from_user.id

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
        email = generate_temp_gmail()
        context.user_data["temp_gmail"] = email
        await query.message.reply_text(
            f"✅ Temp Gmail created:\n\n`{email}`\n\n📩 To check inbox, type /inbox",
            parse_mode="Markdown"
        )

    elif query.data == "temp_number":
        fake = generate_fake_temp_number()
        await query.message.reply_text(
            f"📱 Free demo number: `{fake}`\n\n⚠️ This will not receive OTP.",
            parse_mode="Markdown"
        )
        phone, order_id = buy_temp_number()
        if phone:
            context.user_data["temp_order"] = order_id
            await query.message.reply_text(
                f"✅ Paid Temp Number:\n`{phone}`\n\n📩 Use /otp to check SMS",
                parse_mode="Markdown"
            )
        else:
            await query.message.reply_text("⚠️ Paid Temp Number failed to generate.")

    elif query.data == "removebg":
        USER_ACTION[user_id] = "removebg"
        await query.message.reply_text("📸 Send me a photo to remove background.")

    elif query.data == "bgcolor":
        USER_ACTION[user_id] = "bgcolor"
        USER_BGCOLOR[user_id] = "#00FF00"
        await query.message.reply_text("🎨 Send a photo, I will change its background color.")

    elif query.data == "bgimage":
        USER_ACTION[user_id] = "await_bgimage"
        await query.message.reply_text("🖼 Send me the background image first.")

    elif query.data == "resize":
        USER_ACTION[user_id] = "resize"
        USER_RESIZE[user_id] = (512, 512)
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
    except:
        await update.message.reply_text("⚠️ Invalid format. Example: /resize 800 600")


async def inbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = context.user_data.get("temp_gmail")
    if not email:
        await update.message.reply_text("⚠️ Please generate Temp Gmail first.")
        return

    inbox = fetch_inbox(email)
    if not inbox:
        await update.message.reply_text(f"📭 No mails yet for `{email}`")
        return

    msg = inbox[0]
    details = read_message(email, msg["id"])
    await update.message.reply_text(
        f"📩 New Mail:\n\n"
        f"From: `{details['from']}`\n"
        f"Subject: *{details['subject']}*\n\n"
        f"{details.get('textBody', '❌ No text found')}",
        parse_mode="Markdown"
    )


async def otp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.get("temp_order")
    if not order_id:
        await update.message.reply_text("⚠️ Please generate Temp Number first.")
        return

    code = check_sms(order_id)
    if code:
        await update.message.reply_text(f"✅ OTP: `{code}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("📭 No OTP yet, try again later.")


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
            link = upload_to_fileio(out)
            with open(out, "rb") as f:
                await update.message.reply_photo(f, caption=f"✅ Background removed\n📂 {link}")
            os.remove(out)

        elif action == "bgcolor":
            color = USER_BGCOLOR.get(user_id, "#00FF00")
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
            link = upload_to_fileio(out)
            with open(out, "rb") as f:
                await update.message.reply_photo(f, caption=f"✅ Background replaced\n📂 {link}")
            os.remove(out)

        elif action == "resize":
            w, h = USER_RESIZE.get(user_id, (512, 512))
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
    user_id = update.effective_user.id
    action = USER_ACTION.get(user_id)
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
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("resize", resize_command))
    app.add_handler(CommandHandler("inbox", inbox_command))
    app.add_handler(CommandHandler("otp", otp_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
    
