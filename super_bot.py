#!/usr/bin/env python3
"""
super_bot.py
Final Super Telegram Bot (All Features + Monetag + Submenus)
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
REMOVE_BG_API = os.getenv("REMOVE_BG_API", "YOUR_REMOVE_BG_API_KEY")
TMP_DIR = tempfile.gettempdir()
FILEIO_ENDPOINT = "https://file.io"

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
    return InlineKeyboardMarkup
