import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from twilio.rest import Client

# ====== CONFIG ======
BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789
CHANNEL_USERNAME = "@yourchannel"

TWILIO_SID = "YOUR_TWILIO_SID"
TWILIO_AUTH = "YOUR_TWILIO_AUTH"
TWILIO_NUMBER = "+1234567890"

BASE_URL = "https://yourdomain.com"

# =====================

app = Flask(__name__)
application = ApplicationBuilder().token(BOT_TOKEN).build()
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

users_db = {}
number_owner = {}

# ========= FORCE JOIN CHECK =========
async def is_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users_db[user.id] = user.id

    if not await is_joined(user.id, context):
        keyboard = [
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("I Have Joined ✅", callback_data="verify_join")]
        ]
        await update.message.reply_text(
            "⚠️ Please join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await show_menu(update, context)

# ========= VERIFY BUTTON =========
async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await is_joined(query.from_user.id, context):
        await show_menu(query, context)
    else:
        await query.edit_message_text("❌ You must join the channel first!")

# ========= MENU =========
async def show_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("📱 Get Number", callback_data="get_number")],
        [InlineKeyboardButton("📢 Updates Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("🆘 Support", url="https://t.me/your_support")]
    ]

    text = "✅ Welcome! Choose an option below:"

    if isinstance(update, Update):
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ========= GET NUMBER =========
async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    number = TWILIO_NUMBER  # static for demo
    number_owner[number] = query.from_user.id

    await query.edit_message_text(f"📲 Your Temp Number:\n{number}\n\nSend OTP to this number.")

# ========= ADMIN BROADCAST =========
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    message = " ".join(context.args)
    for user_id in users_db:
        try:
            await context.bot.send_message(user_id, f"📢 Admin Update:\n{message}")
        except:
            pass

    await update.message.reply_text("✅ Broadcast Sent!")

# ========= TWILIO WEBHOOK =========
@app.route("/sms", methods=["POST"])
def sms_webhook():
    from_number = request.form.get("To")
    body = request.form.get("Body")

    if from_number in number_owner:
        user_id = number_owner[from_number]
        application.bot.send_message(chat_id=user_id, text=f"🔐 OTP Received:\n{body}")

    return "OK", 200

# ========= HANDLERS =========
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(CallbackQueryHandler(verify_join, pattern="verify_join"))
application.add_handler(CallbackQueryHandler(get_number, pattern="get_number"))

# ========= MAIN =========
if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=f"{BASE_URL}/{BOT_TOKEN}"
  )
