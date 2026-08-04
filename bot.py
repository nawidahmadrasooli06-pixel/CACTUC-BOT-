import os
import re
import logging
import random
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
CHANNEL_LINK = "https://t.me/CROOK_Cake"

MENU_NORMAL = "✍️ ارسال پیام"
MENU_ANON = "🕵️ ارسال پیام ناشناس"
MENU_PROFILE = "👤 مشخصات من"
MENU_CHANNEL = "📢 کانال من"
MENU_FUN = "🎉 سرگرمی"

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [MENU_NORMAL, MENU_ANON],
        [MENU_PROFILE, MENU_CHANNEL],
        [MENU_FUN],
    ],
    resize_keyboard=True,
)

PROFILE_TEXT = (
    "👤 *مشخصات من*\n\n"
    "اسم: نوید کاکتوس عظیمی\n"
    "سن: ۲۰\n"
    "قد: ۱٫۸۳\n"
    "زادگاه: هرات، افغانستان 🇦🇫\n"
    "سکونت فعلی: آلمان 🇩🇪\n"
    "شغل: در حال تحصیل رشته‌ی دلخواهم\n\n"
    "🌱 *شعار من:* هر روز یه قدم، حتی کوچیک، بازم قدمه."
)

# In-memory map: forwarded-message-id (in admin chat) -> original sender's chat_id
# (best-effort fallback for anonymous messages; survives only until the bot restarts)
reply_map = {}

PHOTOS_DIR = "photos"


def find_target_id(replied_message):
    """Get the original sender's id from a forwarded message: first try
    parsing it directly from the message text (works even after a restart),
    then fall back to the in-memory map (for anonymous messages)."""
    if replied_message.text:
        match = re.search(r"id:\s*(\d+)", replied_message.text)
        if match:
            return int(match.group(1))
    return reply_map.get(replied_message.message_id)

# ---- Fun content ----
JOKES = [
    "یارو میره دکتر میگه دکتر من فراموشی دارم، دکتر میگه از کی؟ میگه از کی چی؟ 😂",
    "چرا کامپیوترا سرما نمی‌خورن؟ چون پنجره دارن، ویندوز باز می‌کنن 😅",
    "به دوستم گفتم چرا انقد دیر جواب میدی؟ گفت داشتم فکر می‌کردم... هنوزم داره فکر می‌کنه 🤔",
]
RIDDLES = [
    "چیه که هرچی ازش برداری بزرگ‌تر میشه؟ (جواب: چاله)",
    "چه چیزیه که شب میاد و روز میره ولی خودش نه شب داره نه روز؟ (جواب: خواب)",
    "چیه که دندون داره ولی نمیتونه گاز بگیره؟ (جواب: شونه)",
]
TRUTH_DARE = [
    "حقیقت: بزرگ‌ترین ترست چیه؟",
    "جرأت: به یکی از دوستات پیام بده و بگو دوستش داری 🥹",
    "حقیقت: آخرین باری که گریه کردی کی بود؟",
]
BIO_TEXTS = [
    "یه رویا، هزارتا تلاش 🌱",
    "زندگی کوتاهه، لبخند بزن 🤍",
    "در حال ساختن آینده‌ای که سزاوارشم ✨",
]
STORY_TEXTS = [
    "یه روز خوب دیگه، یه قدم دیگه به جلو 🚶‍♂️✨",
    "امروز رو با انرژی مثبت شروع کردم 🌤️",
    "گاهی سکوت، قشنگ‌ترین جوابه 🤍",
]
FLIRTY_LINES = [
    "اگه ستاره‌ها رو بشمارم، بازم کمتر از چشمای تو میشن ✨",
    "امروز روزته که یکی بهت بگه لبخندت دنیارو قشنگ‌تر می‌کنه 🥹",
    "دلم برات تنگ نمیشه، چون همیشه یه گوشه از فکرمی 🤍",
]

FUN_CATEGORIES = {
    "joke": ("😂 جوک", JOKES),
    "riddle": ("🧩 چیستان", RIDDLES),
    "truth_dare": ("🎯 جرأت یا حقیقت", TRUTH_DARE),
    "bio": ("📝 متن بیو", BIO_TEXTS),
    "story": ("📸 متن استوری", STORY_TEXTS),
    "flirty": ("💌 دلبری عاشقانه", FLIRTY_LINES),
}

FUN_MENU = InlineKeyboardMarkup(
    [[InlineKeyboardButton(label, callback_data=key)] for key, (label, _) in FUN_CATEGORIES.items()]
    + [[InlineKeyboardButton("🖼️ عکس پروفایل", callback_data="photo")]]
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "normal"
    await update.message.reply_text(
        "سلام! خوش اومدی 👋\n\n"
        "پیامتو بنویس، برای نوید جان ارسال میشه.\n"
        "همچنین می‌تونی از منوی پایین هم استفاده کنی 👇",
        reply_markup=MAIN_MENU,
    )


async def send_fun_menu(update: Update):
    await update.message.reply_text("یکی رو انتخاب کن 👇", reply_markup=FUN_MENU)


async def fun_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data

    if key == "photo":
        if os.path.isdir(PHOTOS_DIR):
            files = [f for f in os.listdir(PHOTOS_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        else:
            files = []

        if not files:
            await query.message.reply_text("🖼️ عکس‌های پروفایل به‌زودی اضافه میشن!")
            return

        chosen = random.choice(files)
        with open(os.path.join(PHOTOS_DIR, chosen), "rb") as photo_file:
            await query.message.reply_photo(photo=photo_file)
        return

    if key in FUN_CATEGORIES:
        label, items = FUN_CATEGORIES[key]
        await query.message.reply_text(f"{label}:\n\n{random.choice(items)}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    # --- Admin replying to a forwarded message ---
    if user.id == ADMIN_ID and update.message.reply_to_message:
        target_chat_id = find_target_id(update.message.reply_to_message)
        if target_chat_id:
            await context.bot.send_message(chat_id=target_chat_id, text=text)
            await update.message.reply_text("پیامت براش ارسال شد ✅")
        else:
            await update.message.reply_text("این پیام قابل ریپلای نیست (خیلی قدیمیه یا ربات ری‌استارت شده).")
        return

    # --- Menu button taps ---
    if text == MENU_NORMAL:
        context.user_data["mode"] = "normal"
        await update.message.reply_text("باشه، پیامتو بنویس 👇")
        return
    if text == MENU_ANON:
        context.user_data["mode"] = "anon"
        await update.message.reply_text("باشه، پیام ناشناس بنویس 👇 (اسمت دیده نمیشه)")
        return
    if text == MENU_PROFILE:
        await update.message.reply_text(PROFILE_TEXT, parse_mode="Markdown")
        return
    if text == MENU_CHANNEL:
        await update.message.reply_text(f"📢 کانال من:\n{CHANNEL_LINK}")
        return
    if text == MENU_FUN:
        await send_fun_menu(update)
        return

    # --- Admin sending a normal (non-reply) message: just acknowledge ---
    if user.id == ADMIN_ID:
        await update.message.reply_text("این پیام رو خودت داری می‌بینی. برای جواب دادن به یه نفر، رو پیامش Reply بزن.")
        return

    # --- Regular incoming message from a user, forward to admin ---
    mode = context.user_data.get("mode", "normal")
    if mode == "anon":
        forward_text = f"🕵️ پیام ناشناس:\n\n{text}"
    else:
        forward_text = (
            f"✍️ پیام از {user.full_name} "
            f"(@{user.username if user.username else 'بدون‌یوزرنیم'} | id: {user.id}):\n\n{text}"
        )

    sent = await context.bot.send_message(chat_id=ADMIN_ID, text=forward_text)
    reply_map[sent.message_id] = user.id
    await update.message.reply_text("پیامت ارسال شد ✅")

    context.user_data["mode"] = "normal"


def main():
    app_request = HTTPXRequest(
        connect_timeout=30,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=30,
    )
    app = ApplicationBuilder().token(BOT_TOKEN).request(app_request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(fun_button))
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
