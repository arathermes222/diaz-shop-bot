#!/usr/bin/env python3
"""Diaz Shop - Telegram Bot for VPN Config Sales"""

import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Config
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@diazplaylist")
OWNER_ID = int(os.environ.get("OWNER_ID", "6326889425"))
SUPPORT_USERNAME = "MrArat"
CARD_NUMBER = "6219861825198608"
CARD_NAME = "امیرمحمد زارعی"
CONFIGS_FILE = "configs.json"

# Config Plans
CONFIG_PLANS = {
    "10gb": {"name": "۱۰ گیگ", "price": "۱۲,۰۰۰", "data": "10GB", "duration": "۱ ماه"},
    "20gb": {"name": "۲۰ گیگ", "price": "۳۰,۰۰۰", "data": "20GB", "duration": "۱ ماه"},
    "50gb": {"name": "۵۰ گیگ", "price": "۷۰,۰۰۰", "data": "50GB", "duration": "۱ ماه"},
    "80gb": {"name": "۸۰ گیگ", "price": "۱۱۰,۰۰۰", "data": "80GB", "duration": "۱ ماه"},
}

# ExpressVPN Plans
EXPRESS_PLANS = {
    "1m": {"name": "۱ ماهه", "price": "۲۲۰,۰۰۰"},
    "3m": {"name": "۳ ماهه", "price": "۳۳۰,۰۰۰"},
    "6m": {"name": "۶ ماهه", "price": "۴۹۰,۰۰۰"},
    "1y": {"name": "۱ ساله", "price": "۹۵۰,۰۰۰"},
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Helper Functions ---

def load_configs():
    if os.path.exists(CONFIGS_FILE):
        with open(CONFIGS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_configs(data):
    with open(CONFIGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def is_member(chat_username: str, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_username, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return True

# --- Bot Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await is_member(CHANNEL_ID, user.id, context):
        keyboard = [[InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
                     [InlineKeyboardButton("✅ عضو شدم", callback_data="check_member")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ برای استفاده از ربات ابتدا باید در کانال عضو شوید!\n\n"
            " روی دکمه زیر کلیک کنید و عضو شوید، سپس دکمه «عضو شدم» را بزنید.",
            reply_markup=reply_markup
        )
        return

    await send_welcome(update, context)

async def check_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_member(CHANNEL_ID, query.from_user.id, context):
        await query.edit_message_text(
            "❌ هنوز عضو کانال نشدید!\n"
            "اول عضو شوید و دوباره دکمه «عضو شدم» را بزنید."
        )
        return

    await query.edit_message_text("✅ عضویت تایید شد!")
    await send_welcome(update, context)

async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("📦 خرید کانفیگ", callback_data="buy_config")],
        [InlineKeyboardButton("🔐 خرید ExpressVPN", callback_data="buy_express")],
        [InlineKeyboardButton("👤 پنل کاربری", callback_data="user_panel")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"🎮 به ربات اختصاصی **Diaz Shop** خوش آمدید {user.first_name}!\n\n"
        " کانفیگ‌های ما زیر قیمت و تضمینی هستند! ✅\n\n"
        f" پشتیبانی: @{SUPPORT_USERNAME}\n"
        "━━━━━━━━━━━━━━━━"
    )

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# --- Config Purchase Flow ---

async def buy_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📦 ۱۰ گیگ - ۱۲,۰۰۰ تومان", callback_data="config_10gb")],
        [InlineKeyboardButton("📦 ۲۰ گیگ - ۳۰,۰۰۰ تومان", callback_data="config_20gb")],
        [InlineKeyboardButton("📦 ۵۰ گیگ - ۷۰,۰۰۰ تومان", callback_data="config_50gb")],
        [InlineKeyboardButton("📦 ۸۰ گیگ - ۱۱۰,۰۰۰ تومان", callback_data="config_80gb")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📦 **انتخاب پلن کانفیگ:**\n\n"
        " همه پلن‌ها یک ماهه هستند.\n"
        "━━━━━━━━━━━━━━━━",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def select_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_id = query.data.replace("config_", "")
    plan = CONFIG_PLANS.get(plan_id)
    if not plan:
        return

    keyboard = [
        [InlineKeyboardButton("💳 خرید", callback_data=f"pay_config_{plan_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_config")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"📦 **پلن انتخابی:** {plan['name']}\n"
        f"💰 **قیمت:** {plan['price']} تومان\n"
        f"⏰ **مدت:** {plan['duration']}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        " روی «خرید» کلیک کنید تا ادامه دهید.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def pay_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_id = query.data.replace("pay_config_", "")
    plan = CONFIG_PLANS.get(plan_id)
    if not plan:
        return

    keyboard = [
        [InlineKeyboardButton("📸 ارسال رسید", callback_data=f"receipt_{plan_id}")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"💳 **اطلاعات پرداخت:**\n\n"
        f"💰 **مبلغ:** {plan['price']} تومان\n"
        f"📦 **پلن:** {plan['name']} ({plan['duration']})\n\n"
        f"🏦 **شماره کارت:**\n`{CARD_NUMBER}`\n"
        f"👤 **به نام:** {CARD_NAME}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "💰 مبلغ را به شماره کارت واریز کنید.\n"
        "📸 سپس رسید پرداخت را ارسال کنید.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def receipt_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_id = query.data.replace("receipt_", "")
    plan = CONFIG_PLANS.get(plan_id)
    if not plan:
        return

    await query.edit_message_text(
        "📸 **لطفاً رسید پرداخت را ارسال کنید:**\n\n"
        " (عکس رسید را اینجا بفرستید)\n"
        "━━━━━━━━━━━━━━━━"
    )

    context.user_data["waiting_receipt"] = True
    context.user_data["receipt_plan"] = plan_id
    context.user_data["receipt_type"] = "config"

# --- ExpressVPN Purchase Flow ---

async def buy_express(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "🔐 **ExpressVPN**\n\n"
        " • اسپانسر رسمی جام جهانی ۲۰۲۶\n"
        " • دارای قابلیت Killswitch\n"
        " • دارای پروتکل‌های قدرمند\n"
        " • قابلیت اتصال در تمامی دستگاه‌ها\n"
        " • قابلیت مسدودسازی تبلیغات\n"
        " • قابلیت Auto Connect\n"
        " • دارای ۳۰۰ سرور از ۱۰۰ کشور\n"
        " • دارای آیپی‌های ثابت\n"
        " • مناسب گیمینگ\n"
        " • مناسب اینستاگرام\n"
        " • مناسب دانلود و آپلود\n"
        " • سرعت بی‌نظیر\n"
        " • سرورهای قدرمند و نامحدود\n\n"
        "━━━━━━━━━━━━━━━━\n"
        " **انتخاب پلن:**"
    )

    keyboard = [
        [InlineKeyboardButton("⏰ ۱ ماهه - ۲۲۰,۰۰۰ تومان", callback_data="express_1m")],
        [InlineKeyboardButton("⏰ ۳ ماهه - ۳۳۰,۰۰۰ تومان", callback_data="express_3m")],
        [InlineKeyboardButton("⏰ ۶ ماهه - ۴۹۰,۰۰۰ تومان", callback_data="express_6m")],
        [InlineKeyboardButton("⏰ ۱ ساله - ۹۵۰,۰۰۰ تومان", callback_data="express_1y")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def select_express(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_id = query.data.replace("express_", "")
    plan = EXPRESS_PLANS.get(plan_id)
    if not plan:
        return

    keyboard = [
        [InlineKeyboardButton("💳 خرید", callback_data=f"pay_express_{plan_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_express")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"🔐 **پلن انتخابی:** {plan['name']}\n"
        f"💰 **قیمت:** {plan['price']} تومان\n\n"
        "━━━━━━━━━━━━━━━━\n"
        " روی «خرید» کلیک کنید تا ادامه دهید.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def pay_express(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_id = query.data.replace("pay_express_", "")
    plan = EXPRESS_PLANS.get(plan_id)
    if not plan:
        return

    keyboard = [
        [InlineKeyboardButton("📸 ارسال رسید", callback_data=f"receipt_express_{plan_id}")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"💳 **اطلاعات پرداخت:**\n\n"
        f"💰 **مبلغ:** {plan['price']} تومان\n"
        f"📦 **پلن:** {plan['name']}\n\n"
        f"🏦 **شماره کارت:**\n`{CARD_NUMBER}`\n"
        f"👤 **به نام:** {CARD_NAME}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "💰 مبلغ را به شماره کارت واریز کنید.\n"
        "📸 سپس رسید پرداخت را ارسال کنید.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def receipt_express_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_id = query.data.replace("receipt_express_", "")
    plan = EXPRESS_PLANS.get(plan_id)
    if not plan:
        return

    await query.edit_message_text(
        "📸 **لطفاً رسید پرداخت را ارسال کنید:**\n\n"
        " (عکس رسید را اینجا بفرستید)\n"
        "━━━━━━━━━━━━━━━━"
    )

    context.user_data["waiting_receipt"] = True
    context.user_data["receipt_plan"] = plan_id
    context.user_data["receipt_type"] = "express"

# --- User Panel ---

async def user_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    configs = load_configs()
    user_configs = configs.get(user_id, [])

    if not user_configs:
        text = (
            "👤 **پنل کاربری:**\n\n"
            " شما هنوز هیچ کانفیگی ندارید.\n"
            "━━━━━━━━━━━━━━━━"
        )
    else:
        text = "👤 **پنل کاربری:**\n\n"
        for i, cfg in enumerate(user_configs, 1):
            text += f" **{i}.** {cfg.get('type', 'کانفیگ')} - {cfg.get('data', '')}\n"
            text += f"    🔗 `{cfg.get('link', 'نامشخص')}`\n\n"
        text += "━━━━━━━━━━━━━━━━"

    keyboard = [
        [InlineKeyboardButton("📦 خرید کانفیگ", callback_data="buy_config")],
        [InlineKeyboardButton("🔐 خرید ExpressVPN", callback_data="buy_express")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    keyboard = [
        [InlineKeyboardButton("📦 خرید کانفیگ", callback_data="buy_config")],
        [InlineKeyboardButton("🔐 خرید ExpressVPN", callback_data="buy_express")],
        [InlineKeyboardButton("👤 پنل کاربری", callback_data="user_panel")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"🎮 به ربات اختصاصی **Diaz Shop** خوش آمدید {user.first_name}!\n\n"
        " کانفیگ‌های ما زیر قیمت و تضمینی هستند! ✅\n\n"
        f" پشتیبانی: @{SUPPORT_USERNAME}\n"
        "━━━━━━━━━━━━━━━━"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# --- Handle Receipt ---

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_receipt"):
        return

    user = update.effective_user
    plan_id = context.user_data.get("receipt_plan")
    plan_type = context.user_data.get("receipt_type")

    if plan_type == "config":
        plan = CONFIG_PLANS.get(plan_id)
    else:
        plan = EXPRESS_PLANS.get(plan_id)

    if not plan:
        return

    context.user_data["waiting_receipt"] = False

    caption = (
        f"📸 **رسید جدید!**\n\n"
        f"👤 **کاربر:** {user.first_name} (@{user.username or 'ندارد'})\n"
        f"🆔 **آیدی:** {user.id}\n"
        f"📦 **پلن:** {plan['name']}\n"
        f"💰 **مبلغ:** {plan['price']} تومان\n"
        f"📦 **نوع:** {'کانفیگ' if plan_type == 'config' else 'ExpressVPN'}"
    )

    keyboard = [
        [InlineKeyboardButton("✅ تایید و ارسال کانفیگ", callback_data=f"approve_{plan_type}_{user.id}_{plan_id}")],
        [InlineKeyboardButton("❌ رد", callback_data=f"reject_{user.id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(
        chat_id=OWNER_ID,
        photo=update.message.photo[-1].file_id,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ رسید شما دریافت شد!\n"
        " تا چند دقیقه بررسی و تایید می‌شود.\n"
        "━━━━━━━━━━━━━━━━"
    )

# --- Admin Approve Flow ---

async def approve_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    plan_type = parts[1]
    user_id = int(parts[2])
    plan_id = parts[3]

    if plan_type == "config":
        plan = CONFIG_PLANS.get(plan_id)
    else:
        plan = EXPRESS_PLANS.get(plan_id)

    # Store pending approval info for admin
    context.bot_data[f"pending_approve_{OWNER_ID}"] = {
        "user_id": user_id,
        "plan_type": plan_type,
        "plan_id": plan_id,
        "plan_name": plan["name"] if plan else plan_id,
    }

    await query.edit_message_caption(
        caption=query.message.caption + "\n\n⏳ **در حال ارسال کانفیگ...**",
        parse_mode="Markdown"
    )

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=(
            f"📝 **لطفاً لینک کانفیگ/اشتراک رو بفرست:**\n\n"
            f"👤 **کاربر:** {user_id}\n"
            f"📦 **پلن:** {plan['name'] if plan else plan_id}\n\n"
            "لینک رو تایپ کن و بفرست 👇"
        ),
        parse_mode="Markdown"
    )

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin text messages (config links)."""
    if update.effective_user.id != OWNER_ID:
        return

    pending = context.bot_data.get(f"pending_approve_{OWNER_ID}")
    if not pending:
        return

    config_link = update.message.text.strip()
    user_id = pending["user_id"]
    plan_type = pending["plan_type"]
    plan_id = pending["plan_id"]
    plan_name = pending["plan_name"]

    # Save config for user
    configs = load_configs()
    user_id_str = str(user_id)
    if user_id_str not in configs:
        configs[user_id_str] = []

    configs[user_id_str].append({
        "type": "کانفیگ" if plan_type == "config" else "ExpressVPN",
        "data": plan_name,
        "link": config_link,
    })
    save_configs(configs)

    # Send config to user
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"✅ **پرداخت شما تایید شد!**\n\n"
            f"📦 **پلن:** {plan_name}\n"
            f"🔗 **لینک کانفیگ:**\n`{config_link}`\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "از خرید شما متشکریم! 🙏"
        ),
        parse_mode="Markdown"
    )

    # Notify admin
    await update.message.reply_text(
        f"✅ **کانفیگ با موفقیت ارسال شد!**\n\n"
        f"👤 کاربر: {user_id}\n"
        f"📦 پلن: {plan_name}"
    )

    # Clear pending
    del context.bot_data[f"pending_approve_{OWNER_ID}"]

async def reject_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split("_")[1])

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "❌ **رسید شما تایید نشد.**\n\n"
            " لطفاً با پشتیبانی تماس بگیرید.\n"
            f" 💬 @{SUPPORT_USERNAME}\n"
            "━━━━━━━━━━━━━━━━"
        ),
        parse_mode="Markdown"
    )

    await query.edit_message_caption(
        caption=query.message.caption + "\n\n❌ **رد شد!**",
        parse_mode="Markdown"
    )

# --- Main ---

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))

    # Callback query handlers
    app.add_handler(CallbackQueryHandler(check_member, pattern="^check_member$"))
    app.add_handler(CallbackQueryHandler(buy_config, pattern="^buy_config$"))
    app.add_handler(CallbackQueryHandler(select_config, pattern="^config_"))
    app.add_handler(CallbackQueryHandler(pay_config, pattern="^pay_config_"))
    app.add_handler(CallbackQueryHandler(buy_express, pattern="^buy_express$"))
    app.add_handler(CallbackQueryHandler(select_express, pattern="^express_"))
    app.add_handler(CallbackQueryHandler(pay_express, pattern="^pay_express_"))
    app.add_handler(CallbackQueryHandler(user_panel, pattern="^user_panel$"))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(approve_receipt, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_receipt, pattern="^reject_"))

    # Handle receipts for config
    app.add_handler(CallbackQueryHandler(receipt_received, pattern="^receipt_(?!express_)"))
    app.add_handler(CallbackQueryHandler(receipt_express_received, pattern="^receipt_express_"))

    # Photo handler for receipts
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Text handler for admin config links
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text))

    logger.info("Diaz Shop Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
