import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ======================
# Config
# ======================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
MONITAG_LINK = "https://otieu.com/4/9875089"
logging.basicConfig(level=logging.INFO)

# ======================
# Start / Main Menu
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📧 Temp Gmail", callback_data="temp_gmail")],
        [InlineKeyboardButton("📱 Temp Number", callback_data="temp_number")],
        [InlineKeyboardButton("📹 Video Downloader", callback_data="video_menu")],
        [InlineKeyboardButton("🖼 Photo Tools", callback_data="photo_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✨ Main Menu:", reply_markup=reply_markup)

# ======================
# Callback Handler
# ======================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # ===== Main Menu =====
    if query.data == "temp_gmail":
        await query.edit_message_text("📧 Temp Gmail created successfully!")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"🔗 {MONITAG_LINK}")

    elif query.data == "temp_number":
        await query.edit_message_text("📱 Temp Number generated!")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"🔗 {MONITAG_LINK}")

    elif query.data == "video_menu":
        keyboard = [
            [InlineKeyboardButton("▶ YouTube", callback_data="yt_dl")],
            [InlineKeyboardButton("📘 Facebook", callback_data="fb_dl")],
            [InlineKeyboardButton("🎵 TikTok", callback_data="tt_dl")],
            [InlineKeyboardButton("📸 Instagram", callback_data="ig_dl")],
            [InlineKeyboardButton("⬅ Back", callback_data="main_menu")]
        ]
        await query.edit_message_text("📹 Choose Platform:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "photo_menu":
        keyboard = [
            [InlineKeyboardButton("❌ Remove Background", callback_data="bg_remove")],
            [InlineKeyboardButton("🎨 Change Color", callback_data="bg_color")],
            [InlineKeyboardButton("🖼 Replace Background", callback_data="bg_replace")],
            [InlineKeyboardButton("📏 Resize Image", callback_data="resize_img")],
            [InlineKeyboardButton("⬅ Back", callback_data="main_menu")]
        ]
        await query.edit_message_text("🖼 Photo Tools:", reply_markup=InlineKeyboardMarkup(keyboard))

    # ===== Video Downloaders =====
    elif query.data in ["yt_dl", "fb_dl", "tt_dl", "ig_dl"]:
        platform = query.data.split("_")[0].upper()
        await query.edit_message_text(f"📥 Send me {platform} link to download...")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"🔗 {MONITAG_LINK}")

    # ===== Photo Tools =====
    elif query.data == "bg_remove":
        await query.edit_message_text("❌ Background removed! (Upload Image)")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"🔗 {MONITAG_LINK}")

    elif query.data == "bg_color":
        await query.edit_message_text("🎨 Send me color code to change background.")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"🔗 {MONITAG_LINK}")

    elif query.data == "bg_replace":
        await query.edit_message_text("🖼 Send new background image.")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"🔗 {MONITAG_LINK}")

    elif query.data == "resize_img":
        await query.edit_message_text("📏 Send size (e.g. 800x600) to resize image.")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"🔗 {MONITAG_LINK}")

    # ===== Back to Main Menu =====
    elif query.data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("📧 Temp Gmail", callback_data="temp_gmail")],
            [InlineKeyboardButton("📱 Temp Number", callback_data="temp_number")],
            [InlineKeyboardButton("📹 Video Downloader", callback_data="video_menu")],
            [InlineKeyboardButton("🖼 Photo Tools", callback_data="photo_menu")],
        ]
        await query.edit_message_text("✨ Main Menu:", reply_markup=InlineKeyboardMarkup(keyboard))

# ======================
# Main
# ======================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
                              
