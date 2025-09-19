#!/usr/bin/env python3
"""
Super Telegram Bot
Features:
 - Start menu with Monetag links
 - Background remover (remove.bg)
 - Background color replace
 - Background image replace
 - Pic size converter (user sets size with /resize WxH)
 - Video downloader (yt-dlp) for links
 - Upload processed tmp files to file.io and return link
Requirements:
 - python-telegram-bot==20.3
 - requests
 - Pillow
 - yt-dlp
"""

import os
import tempfile
import uuid
import shutil
import requests
import asyncio

from pathlib import Path
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

from PIL import Image

# ---------- CONFIG ----------
# Put your bot token in environment variable TELEGRAM_TOKEN (recommended)
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "7948273306:AAGY2ri4iKlYxzuVVnKl-5_zXoh7_QKL-fE")

# Monetag direct link to attach to buttons
MONETAG_LINK = "https://otieu.com/4/9875089"

# Remove.bg API key (set as env var REMOVE_BG_API or paste here for testing)
REMOVE_BG_API = os.getenv("REMOVE_BG_API", "YOUR_REMOVE_BG_API_KEY")

# file.io upload endpoint (for temporary file hosting)
FILEIO_ENDPOINT = "https://file.io"

# Temporary storage dir
TMP_DIR = tempfile.gettempdir()

# ---------- STATE (in-memory) ----------
# Track what action a user requested before sending an image
USER_ACTION = {}        # user_id -> action string: "removebg"/"resize"/"bgcolor"/"bgimage"
USER_RESIZE = {}        # user_id -> (w,h)
USER_BGCOLOR = {}       # user_id -> color string (name or hex)
USER_BGIMAGE = {}       # user_id -> path to uploaded background image (local path)
# NOTE: in production you'd persist these if needed

# ---------- UTILITIES ----------

def unique_path(suffix: str):
    return os.path.join(TMP_DIR, f"{uuid.uuid4().hex}{suffix}")

def upload_to_fileio(path: str) -> str | None:
    """Upload a file to file.io and return the link (or None)."""
    try:
        with open(path, "rb") as f:
            res = requests.post(FILEIO_ENDPOINT, files={"file": f})
        if res.status_code == 200:
            j = res.json()
            return j.get("link")
    except Exception:
        pass
    return None

async def run_blocking(func, *args, **kwargs):
    """Run blocking I/O in thread to avoid blocking event loop."""
    return await asyncio.get_event_loop().run_in_executor(None, lambda: func(*args, **kwargs))

# ---------- IMAGE / REMOVE.BG HELPERS ----------

def call_removebg_api(input_path: str, output_path: str, bg_color: str | None = None) -> bool:
    """
    Call remove.bg sync API.
    If bg_color is provided, pass bg_color param to API to get colored background.
    Returns True on success and writes output_path.
    """
    if not REMOVE_BG_API or REMOVE_BG_API == "YOUR_REMOVE_BG_API_KEY":
        return False

    with open(input_path, "rb") as img_file:
        data = {"size": "auto"}
        if bg_color:
            data["bg_color"] = bg_color
        try:
            r = requests.post(
                "https://api.remove.bg/v1.0/removebg",
                files={"image_file": img_file},
                data=data,
                headers={"X-Api-Key": REMOVE_BG_API},
                timeout=60
            )
        except Exception:
            return False

    if r.status_code == 200:
        with open(output_path, "wb") as out:
            out.write(r.content)
        return True
    else:
        return False

def composite_with_bgimage(foreground_png_path: str, bg_image_path: str, out_path: str) -> bool:
    """
    Composite a foreground PNG with alpha over background image.
    foreground_png_path must be RGBA (alpha preserved).
    """
    try:
        fg = Image.open(foreground_png_path).convert("RGBA")
        bg = Image.open(bg_image_path).convert("RGBA")

        # Resize background to foreground size
        bg = bg.resize(fg.size, Image.LANCZOS)
        composed = Image.alpha_composite(bg, fg)
        # save as PNG
        composed.convert("RGB").save(out_path, format="PNG")
        return True
    except Exception:
        return False

# ---------- TELEGRAM HANDLERS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📧 Temp Mail", url=MONETAG_LINK)],
        [InlineKeyboardButton("📱 Temp Number", url=MONETAG_LINK)],
        [InlineKeyboardButton("🖼️ Photo Edit", url=MONETAG_LINK)],
        [InlineKeyboardButton("✨ Remini HD", url=MONETAG_LINK)],
        [InlineKeyboardButton("🎥 Video Downloader", url=MONETAG_LINK)],
        [InlineKeyboardButton("🖼️ Background Remover", callback_data="removebg")],
        [InlineKeyboardButton("🎨 BG Color Change", callback_data="bgcolor")],
        [InlineKeyboardButton("🖼️ BG Image Replace", callback_data="bgimage")],
        [InlineKeyboardButton("📏 Pic Size Converter", callback_data="resize")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Welcome! Choose a tool below 👇\n(Buttons with links open Monetag; image features work inside bot)", reply_markup=reply_markup)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "removebg":
        USER_ACTION[user_id] = "removebg"
        await query.message.reply_text("📸 Send me a photo and I'll remove the background.")
    elif query.data == "bgcolor":
        USER_ACTION[user_id] = "bgcolor"
        await query.message.reply_text("🎨 Set color first with `/bgcolor red` or `/bgcolor #FF00FF` then send photo.")
    elif query.data == "bgimage":
        USER_ACTION[user_id] = "bgimage"
        await query.message.reply_text("🖼️ Please send the image you want to use as background. After uploading that, send the target photo to replace background.")
    elif query.data == "resize":
        USER_ACTION[user_id] = "resize"
        await query.message.reply_text("📏 Set size first with `/resize 512x512` then send your photo.")

# /resize WxH
async def resize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /resize WIDTHxHEIGHT e.g. /resize 512x512")
        return
    try:
        size_text = context.args[0].lower()
        w, h = map(int, size_text.split("x"))
        USER_RESIZE[user_id] = (w, h)
        await update.message.reply_text(f"✅ Resize set to {w}x{h}. Now send a photo.")
    except Exception:
        await update.message.reply_text("Invalid format. Use like `/resize 800x600`")

# /bgcolor color
async def bgcolor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /bgcolor red  OR /bgcolor #00FF00")
        return
    color = context.args[0]
    USER_BGCOLOR[user_id] = color
    USER_ACTION[user_id] = "bgcolor"
    await update.message.reply_text(f"✅ Background color set to `{color}`. Now send a photo.", parse_mode="Markdown")

# /bgimage - user will send an image immediately after /bgimage or via button; here we'll set action
async def bgimage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USER_ACTION[user_id] = "await_bgimage"
    await update.message.reply_text("🖼️ Send the background image you'd like to set (this will be reused for future composites).")

# text handler: detect video links
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # very simple check for http(s)
    if text.startswith("http://") or text.startswith("https://"):
        await update.message.reply_text("⏳ Received link — attempting to download (this may take time)...")
        await handle_video_download_link(update, context, text)
    else:
        await update.message.reply_text("⚡ Use the buttons, or send a video link (YouTube/TikTok/FB/IG) to download.")

# Video download using yt-dlp (blocking) — run in thread
def download_video_to_path(url: str, out_path: str) -> tuple[bool, str]:
    import yt_dlp
    ydl_opts = {
        "outtmpl": out_path,
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True, out_path
    except Exception as e:
        return False, str(e)

async def handle_video_download_link(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    tmp_file = unique_path(".mp4")
    ok, result = await run_blocking(download_video_to_path, url, tmp_file)
    if ok:
        # if too large to send directly, upload to file.io
        try:
            size_mb = Path(tmp_file).stat().st_size / (1024*1024)
        except Exception:
            size_mb = 0
        if size_mb < 50:
            # send directly
            with open(tmp_file, "rb") as f:
                await update.message.reply_video(video=f, caption="✅ Download complete")
            os.remove(tmp_file)
        else:
            link = await run_blocking(upload_to_fileio, tmp_file)
            if link:
                await update.message.reply_text(f"📥 File is large. Download from: {link}")
            else:
                await update.message.reply_text("⚠️ File too large to send and upload failed.")
            os.remove(tmp_file)
    else:
        await update.message.reply_text(f"❌ Download failed: {result}")

# Handle photos (many actions)
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    action = USER_ACTION.get(user_id)

    # download incoming photo to temp
    photo_file = await update.message.photo[-1].get_file()
    local_in = unique_path(".jpg")
    await photo_file.download_to_drive(local_in)

    try:
        # 1) If user was setting bgimage (await_bgimage) then save background for that user
        if action == "await_bgimage":
            # save bg image path
            bg_saved_path = unique_path(".png")
            # convert to png to standardize
            img = Image.open(local_in).convert("RGB")
            img.save(bg_saved_path, format="PNG")
            USER_BGIMAGE[user_id] = bg_saved_path
            USER_ACTION[user_id] = None
            await update.message.reply_text("✅ Background image saved. Now send the photo you want to composite foreground onto that background (use BG Image Replace button).")
            return

        # 2) removebg (plain) or bgcolor or bgimage
        if action == "removebg":
            out_png = unique_path(".png")
            ok = await run_blocking(call_removebg_api, local_in, out_png, None)
            if ok:
                # send result and optional file.io link
                with open(out_png, "rb") as f:
                    await update.message.reply_photo(photo=f, caption="✅ Background removed")
                # upload tmp link
                link = await run_blocking(upload_to_fileio, out_png)
                if link:
                    await update.message.reply_text(f"📂 Download link (tmp): {link}")
                os.remove(out_png)
            else:
                await update.message.reply_text("❌ remove.bg failed (check API key/credits).")

        elif action == "bgcolor":
            color = USER_BGCOLOR.get(user_id)
            if not color:
                await update.message.reply_text("⚠️ No color set. Use /bgcolor #RRGGBB or /bgcolor red")
            else:
                out_png = unique_path(".png")
                ok = await run_blocking(call_removebg_api, local_in, out_png, color)
                if ok:
                    with open(out_png, "rb") as f:
                        await update.message.reply_photo(photo=f, caption=f"✅ Background replaced with {color}")
                    link = await run_blocking(upload_to_fileio, out_png)
                    if link:
                        await update.message.reply_text(f"📂 Download link (tmp): {link}")
                    os.remove(out_png)
                else:
                    await update.message.reply_text("❌ remove.bg failed (check API key/credits).")

        elif action == "bgimage":
            # user should have previously set USER_BGIMAGE[user_id]
            bg_path = USER_BGIMAGE.get(user_id)
            if not bg_path or not os.path.exists(bg_path):
                await update.message.reply_text("⚠️ No background image saved. First send /bgimage and upload a background image.")
            else:
                # first get foreground alpha PNG from remove.bg
                fg_png = unique_path(".png")
                ok = await run_blocking(call_removebg_api, local_in, fg_png, None)
                if not ok:
                    await update.message.reply_text("❌ remove.bg failed (check API key/credits).")
                else:
                    out_composed = unique_path(".png")
                    ok2 = await run_blocking(composite_with_bgimage, fg_png, bg_path, out_composed)
                    if ok2:
                        with open(out_composed, "rb") as f:
                            await update.message.reply_photo(photo=f, caption="✅ Replaced background with your image")
                        link = await run_blocking(upload_to_fileio, out_composed)
                        if link:
                            await update.message.reply_text(f"📂 Download link (tmp): {link}")
                        os.remove(out_composed)
                    else:
                        await update.message.reply_text("❌ Failed to composite foreground and background image.")
                    os.remove(fg_png)

        elif action == "resize":
            size = USER_RESIZE.get(user_id)
            if not size:
                await update.message.reply_text("⚠️ Size not set. Use /resize WIDTHxHEIGHT first.")
            else:
                w, h = size
                out = unique_path(".png")
                try:
                    img = Image.open(local_in).convert("RGB")
                    img = img.resize((w, h), Image.LANCZOS)
                    img.save(out, format="PNG")
                    with open(out, "rb") as f:
                        await update.message.reply_photo(photo=f, caption=f"✅ Resized to {w}x{h}")
                    link = await run_blocking(upload_to_fileio, out)
                    if link:
                        await update.message.reply_text(f"📂 Download link (tmp): {link}")
                    os.remove(out)
                except Exception:
                    await update.message.reply_text("❌ Failed to resize image.")
        else:
            # no action selected — prompt user
            await update.message.reply_text("⚠️ Please pick a menu option first (/start) or use a link command.")
    finally:
        # remove incoming file
        try:
            if os.path.exists(local_in):
                os.remove(local_in)
        except Exception:
            pass

# ---------- MAIN ----------
def main():
    if BOT_TOKEN is None or BOT_TOKEN == "" or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Error: Set TELEGRAM_TOKEN environment variable or BOT_TOKEN in code.")
        return
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(CommandHandler("resize", resize_command))
    app.add_handler(CommandHandler("bgcolor", bgcolor_command))
    app.add_handler(CommandHandler("bgimage", bgimage_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
