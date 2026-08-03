import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

MENU_NORMAL = "✍️ ارسال پیام"
MENU_ANON = "🕵️ ارسال پیام ناشناس"

MAIN_MENU = ReplyKeyboardMarkup(
    [[MENU_NORMAL, MENU_ANON]],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "normal"
    await update.message.reply_text(
        "سلام! خوش اومدی 👋\n\n"
        "پیامتو بنویس، برای نوید جان ارسال میشه.\n"
        "همچنین می‌تونی از منوی پایین هم استفاده کنی 👇",
        reply_markup=MAIN_MENU,
    )


async def menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == MENU_NORMAL:
        context.user_data["mode"] = "normal"
        await update.message.reply_text("باشه، پیامتو بنویس 👇")
    elif text == MENU_ANON:
        context.user_data["mode"] = "anon"
        await update.message.reply_text("باشه، پیام ناشناس بنویس 👇 (اسمت دیده نمیشه)")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # If it's a menu button tap, handle separately
    if text in (MENU_NORMAL, MENU_ANON):
        await menu_choice(update, context)
        return

    mode = context.user_data.get("mode", "normal")
    user = update.effective_user

    if mode == "anon":
        forward_text = f"🕵️ پیام ناشناس:\n\n{text}"
    else:
        forward_text = (
            f"✍️ پیام از {user.full_name} "
            f"(@{user.username if user.username else 'بدون‌یوزرنیم'} | id: {user.id}):\n\n{text}"
        )

    await context.bot.send_message(chat_id=ADMIN_ID, text=forward_text)
    await update.message.reply_text("پیامت ارسال شد ✅")

    # reset to normal mode after sending, so default next message is identified
    context.user_data["mode"] = "normal"


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    port = int(os.environ.get("PORT", 8443))
    hostname = os.environ["RENDER_EXTERNAL_HOSTNAME"]
    webhook_url = f"https://{hostname}/{BOT_TOKEN}"

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,
    )


if __name__ == "__main__":
    main()
