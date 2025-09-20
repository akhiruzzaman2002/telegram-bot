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
import numpy as np
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
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "7948273306:AAGY2ri4iKlYxzuVVnKl-5_zXoh7_QKL-fE")  # এখানে নিজের টোকেন বসাও
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
            data = r.json()
            return data.get("link") or data.get("url")
    except Exception as e:
        print("file.io error:", e)
        return None
    return None


def safe_remove(img: Image.Image):
    """rembg output কে PIL.Image বানিয়ে রিটার্ন করবে"""
    fg = remove(img)
    if isinstance(fg, np.ndarray):
        fg = Image.fromarray(fg)
    return fg


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
    if TEMP_NUMBER_API_KEY == "YOUR_5SIM_API_KEY":
        return None, None
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

# (callback_handler, inbox, otp, resize, photo_handler, text_handler সব একই থাকবে,
# শুধু rembg এর জায়গায় safe_remove ব্যবহার করবো।)
