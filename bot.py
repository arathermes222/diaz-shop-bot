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
PENDING_FILE = "pending_state.json"

CONFIG_PLANS = {
    "10gb": {"name": "۱۰ گیگ", "price": "۱۲,۰۰۰", "data": "10GB", "duration": "۱ ماه"},
    "20gb": {"name": "۲۰ گیگ", "price": "۳۰,۰۰۰", "data": "20GB", "duration": "۱ ماه"},
    "50gb": {"name": "۵۰ گیگ", "price": "۷۰,۰۰۰", "data": "50GB", "duration": "۱ ماه"},
    "80gb": {"name": "۸۰ گیگ", "price": "۱۱۰,۰۰۰", "data": "80GB", "duration": "۱ ماه"},
}

EXPRESS_PLANS = {
    "1m": {"name": "۱ ماهه", "price": "۲۲۰,۰۰۰"},
    "3m": {"name": "۳ ماهه", "price": "۳۳۰,۰۰۰"},
    "6m": {"name": "۶ ماهه", "price": "۴۹۰,۰۰۰"},
    "1y": {"name": "۱ ساله", "price": "۹۵۰,۰۰۰"},
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Helpers ---

def load_pending():
    try:
        if os.path.exists(PENDING_FILE):
            with open(PENDING_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"load_pending error: {e}")
    return {}

def save_pending(data):
    try:
        with open(PENDING_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"save_pending error: {e}")

def load_configs():
    try:
        if os.path.exists(CONFIGS_FILE):
            with open(CONFIGS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"load_configs error: {e}")
    return {}

def save_configs(data):
    try:
        with open(CONFIGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"save_configs error: {e}")

async def is_member(chat_username, user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_username, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

# --- Commands ---

async def start(update, context):
    user = update.effective_user
    logger.info(f"START from {user.id} ({user.first_name})")
    if not await is_member(CHANNEL_ID, user.id, context):
        kb = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check_member")]
        ]
        await update.message.reply_text(
            "⚠️ برای استفاده از ربات ابتدا باید در کانال عضو شوید!\n\n"
            " روی دکمه زیر کلیک کنید و عضو شوید، سپس دکمه «عضو شدم» را بزنید.",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return
    await send_welcome_msg(update.message)

async def check_member(update, context):
    query = update.callback_query
    await query.answer()
    logger.info(f"CHECK_MEMBER from {query.from_user.id}")
    if not await is_member(CHANNEL_ID, query.from_user.id, context):
        await query.edit_message_text("❌ هنوز عضو کانال نشدید!\nاول عضو شوید و دوباره دکمه «عضو شدم» را بزنید.")
        return
    await query.message.delete()
    await send_welcome_msg(query.message)

WELCOME_TEXT = (
    "🎮 به ربات اختصاصی Diaz Shop خوش آمدید 🚀!\n\n"
    " محصولات ما زیر قیمت و تضمینی هستند! ✅\n\n"
    "━━━━━━━━━━━━━━━━━\n"
    f" پشتیبانی: @{SUPPORT_USERNAME}"
)

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 خرید کانفیگ", callback_data="buy_config")],
        [InlineKeyboardButton("🔐 خرید ExpressVPN", callback_data="buy_express")],
        [InlineKeyboardButton("👤 پنل کاربری", callback_data="user_panel")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ])

async def send_welcome_msg(message_obj):
    await message_obj.reply_text(WELCOME_TEXT, reply_markup=main_menu_kb())

# --- Config Flow ---

async def buy_config(update, context):
    q = update.callback_query
    await q.answer()
    logger.info(f"BUY_CONFIG from {q.from_user.id}")
    kb = [
        [InlineKeyboardButton("📦 ۱۰ گیگ - ۱۲,۰۰۰ تومان", callback_data="config_10gb")],
        [InlineKeyboardButton("📦 ۲۰ گیگ - ۳۰,۰۰۰ تومان", callback_data="config_20gb")],
        [InlineKeyboardButton("📦 ۵۰ گیگ - ۷۰,۰۰۰ تومان", callback_data="config_50gb")],
        [InlineKeyboardButton("📦 ۸۰ گیگ - ۱۱۰,۰۰۰ تومان", callback_data="config_80gb")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    await q.edit_message_text(
        "📦 **انتخاب پلن کانفیگ:**\n\n همه پلن‌ها یک ماهه هستند.\n━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def select_config(update, context):
    q = update.callback_query
    await q.answer()
    pid = q.data.replace("config_", "")
    plan = CONFIG_PLANS.get(pid)
    if not plan:
        return
    kb = [
        [InlineKeyboardButton("💳 خرید", callback_data=f"pay_config_{pid}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_config")],
    ]
    await q.edit_message_text(
        f"📦 **پلن انتخابی:** {plan['name']}\n💰 **قیمت:** {plan['price']} تومان\n⏰ **مدت:** {plan['duration']}\n\n━━━━━━━━━━━━━━━━━\n روی «خرید» کلیک کنید تا ادامه دهید.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def pay_config(update, context):
    q = update.callback_query
    await q.answer()
    pid = q.data.replace("pay_config_", "")
    plan = CONFIG_PLANS.get(pid)
    if not plan:
        return
    kb = [
        [InlineKeyboardButton("📸 ارسال رسید", callback_data=f"receipt_{pid}")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    await q.edit_message_text(
        f"💳 **اطلاعات پرداخت:**\n\n💰 **مبلغ:** {plan['price']} تومان\n📦 **پلن:** {plan['name']} ({plan['duration']})\n\n🏦 **شماره کارت:**\n`{CARD_NUMBER}`\n👤 **به نام:** {CARD_NAME}\n\n━━━━━━━━━━━━━━━━━\n💰 مبلغ را به شماره کارت واریز کنید.\n📸 سپس رسید پرداخت را ارسال کنید.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def receipt_received(update, context):
    q = update.callback_query
    await q.answer()
    pid = q.data.replace("receipt_", "")
    plan = CONFIG_PLANS.get(pid)
    if not plan:
        return
    await q.edit_message_text(
        "📸 **لطفاً رسید پرداخت را ارسال کنید:**\n\n (عکس رسید را اینجا بفرستید)\n━━━━━━━━━━━━━━━━━"
    )
    uid = str(q.from_user.id)
    pending = load_pending()
    pending[uid] = {"waiting": True, "plan": pid, "type": "config"}
    save_pending(pending)
    logger.info(f"SAVE PENDING: user={uid} state={pending[uid]}")

# --- Express Flow ---

async def buy_express(update, context):
    q = update.callback_query
    await q.answer()
    logger.info(f"BUY_EXPRESS from {q.from_user.id}")
    text = (
        "🔐 **ExpressVPN**\n\n • اسپانسر رسمی جام جهانی ۲۰۲۶\n • دارای قابلیت Killswitch\n • دارای پروتکل‌های قدرمند\n • قابلیت اتصال در تمامی دستگاه‌ها\n • قابلیت مسدودسازی تبلیغات\n • قابلیت Auto Connect\n • دارای ۳۰۰ سرور از ۱۰۰ کشور\n • دارای آیپی‌های ثابت\n • مناسب گیمینگ\n • مناسب اینستاگرام\n • مناسب دانلود و آپلود\n • سرعت بی‌نظیر\n • سرورهای قدرمند و نامحدود\n\n━━━━━━━━━━━━━━━━━\n **انتخاب پلن:**"
    )
    kb = [
        [InlineKeyboardButton("⏰ ۱ ماهه - ۲۲۰,۰۰۰ تومان", callback_data="express_1m")],
        [InlineKeyboardButton("⏰ ۳ ماهه - ۳۳۰,۰۰۰ تومان", callback_data="express_3m")],
        [InlineKeyboardButton("⏰ ۶ ماهه - ۴۹۰,۰۰۰ تومان", callback_data="express_6m")],
        [InlineKeyboardButton("⏰ ۱ ساله - ۹۵۰,۰۰۰ تومان", callback_data="express_1y")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def select_express(update, context):
    q = update.callback_query
    await q.answer()
    pid = q.data.replace("express_", "")
    plan = EXPRESS_PLANS.get(pid)
    if not plan:
        return
    kb = [
        [InlineKeyboardButton("💳 خرید", callback_data=f"pay_express_{pid}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="buy_express")],
    ]
    await q.edit_message_text(
        f"🔐 **پلن انتخابی:** {plan['name']}\n💰 **قیمت:** {plan['price']} تومان\n\n━━━━━━━━━━━━━━━━━\n روی «خرید» کلیک کنید تا ادامه دهید.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def pay_express(update, context):
    q = update.callback_query
    await q.answer()
    pid = q.data.replace("pay_express_", "")
    plan = EXPRESS_PLANS.get(pid)
    if not plan:
        return
    kb = [
        [InlineKeyboardButton("📸 ارسال رسید", callback_data=f"receipt_express_{pid}")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    await q.edit_message_text(
        f"💳 **اطلاعات پرداخت:**\n\n💰 **مبلغ:** {plan['price']} تومان\n📦 **پلن:** {plan['name']}\n\n🏦 **شماره کارت:**\n`{CARD_NUMBER}`\n👤 **به نام:** {CARD_NAME}\n\n━━━━━━━━━━━━━━━━━\n💰 مبلغ را به شماره کارت واریز کنید.\n📸 سپس رسید پرداخت را ارسال کنید.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def receipt_express_received(update, context):
    q = update.callback_query
    await q.answer()
    pid = q.data.replace("receipt_express_", "")
    plan = EXPRESS_PLANS.get(pid)
    if not plan:
        return
    await q.edit_message_text(
        "📸 **لطفاً رسید پرداخت را ارسال کنید:**\n\n (عکس رسید را اینجا بفرستید)\n━━━━━━━━━━━━━━━━━"
    )
    uid = str(q.from_user.id)
    pending = load_pending()
    pending[uid] = {"waiting": True, "plan": pid, "type": "express"}
    save_pending(pending)
    logger.info(f"SAVE PENDING: user={uid} state={pending[uid]}")

# --- User Panel ---

async def user_panel(update, context):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    configs = load_configs()
    user_configs = configs.get(uid, [])
    if not user_configs:
        text = "👤 **پنل کاربری:**\n\n شما هنوز هیچ کانفیگی ندارید.\n━━━━━━━━━━━━━━━━━"
    else:
        text = "👤 **پنل کاربری:**\n\n"
        for i, cfg in enumerate(user_configs, 1):
            text += f" **{i}.** {cfg.get('type', 'کانفیگ')} - {cfg.get('data', '')}\n    🔗 `{cfg.get('link', 'نامشخص')}`\n\n"
        text += "━━━━━━━━━━━━━━━━━"
    kb = [
        [InlineKeyboardButton("📦 خرید کانفیگ", callback_data="buy_config")],
        [InlineKeyboardButton("🔐 خرید ExpressVPN", callback_data="buy_express")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def back_main(update, context):
    q = update.callback_query
    await q.answer()
    text = (
        "🎮 به ربات اختصاصی Diaz Shop خوش آمدید 🚀!\n\n"
        " محصولات ما زیر قیمت و تضمینی هستند! ✅\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        f" پشتیبانی: @{SUPPORT_USERNAME}"
    )
    await q.edit_message_text(text, reply_markup=main_menu_kb())

# --- Handle Receipt Photo ---

async def handle_photo(update, context):
    uid = str(update.effective_user.id)
    logger.info(f"PHOTO from {uid}")

    pending = load_pending()
    logger.info(f"ALL PENDING: {pending}")

    state = pending.get(uid)
    if not state or not state.get("waiting"):
        logger.info(f"No pending receipt for {uid}, ignoring")
        return

    logger.info(f"Processing receipt for {uid}: {state}")

    plan_type = state.get("type", "config")
    plan_id = state.get("plan")
    plan = CONFIG_PLANS.get(plan_id) if plan_type == "config" else EXPRESS_PLANS.get(plan_id)

    if not plan:
        logger.error(f"Plan not found: {plan_type}/{plan_id}")
        return

    del pending[uid]
    save_pending(pending)

    user = update.effective_user
    caption = (
        f"📸 **رسید جدید!**\n\n"
        f"👤 **کاربر:** {user.first_name} (@{user.username or 'ندارد'})\n"
        f"🆔 **آیدی:** {user.id}\n"
        f"📦 **پلن:** {plan['name']}\n"
        f"💰 **مبلغ:** {plan['price']} تومان\n"
        f"📦 **نوع:** {'کانفیگ' if plan_type == 'config' else 'ExpressVPN'}"
    )
    kb = [
        [InlineKeyboardButton("✅ تایید و ارسال کانفیگ", callback_data=f"approve_{plan_type}_{user.id}_{plan_id}")],
        [InlineKeyboardButton("❌ رد", callback_data=f"reject_{user.id}")],
    ]

    try:
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=update.message.photo[-1].file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )
        logger.info(f"Receipt forwarded to owner for {uid}")
    except Exception as e:
        logger.error(f"Failed to forward receipt: {e}")

    kb2 = [[InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back_main")]]
    await update.message.reply_text(
        "✅ رسید شما دریافت شد!\n خیلی زود سفارشت پیگیری و تحویل داده میشه 😉\n━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(kb2)
    )

# --- Admin ---

async def approve_receipt(update, context):
    q = update.callback_query
    await q.answer()
    parts = q.data.split("_")
    plan_type = parts[1]
    user_id = int(parts[2])
    plan_id = parts[3]
    plan = CONFIG_PLANS.get(plan_id) if plan_type == "config" else EXPRESS_PLANS.get(plan_id)

    context.bot_data[f"pending_approve_{OWNER_ID}"] = {
        "user_id": user_id, "plan_type": plan_type, "plan_id": plan_id,
        "plan_name": plan["name"] if plan else plan_id,
    }
    await q.edit_message_caption(
        caption=q.message.caption + "\n\n⏳ **در حال ارسال کانفیگ...**",
        parse_mode="Markdown"
    )
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"📝 **لطفاً لینک کانفیگ/اشتراک رو بفرست:**\n\n👤 **کاربر:** {user_id}\n📦 **پلن:** {plan['name'] if plan else plan_id}\n\nلینک رو تایپ کن و بفرست 👇",
        parse_mode="Markdown"
    )

async def handle_admin_text(update, context):
    if update.effective_user.id != OWNER_ID:
        return
    pending = context.bot_data.get(f"pending_approve_{OWNER_ID}")
    if not pending:
        return

    config_link = update.message.text.strip()
    user_id = pending["user_id"]
    plan_name = pending["plan_name"]
    plan_type = pending["plan_type"]

    configs = load_configs()
    uid_str = str(user_id)
    if uid_str not in configs:
        configs[uid_str] = []
    configs[uid_str].append({"type": "کانفیگ" if plan_type == "config" else "ExpressVPN", "data": plan_name, "link": config_link})
    save_configs(configs)

    kb = [[InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back_main")]]
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ **پرداخت شما تایید شد!**\n\n📦 **پلن:** {plan_name}\n🔗 **لینک کانفیگ:**\n`{config_link}`\n\n━━━━━━━━━━━━━━━━━\nاز خرید شما متشکریم! 🙏",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )
    await update.message.reply_text(f"✅ **کانفیگ با موفقیت ارسال شد!**\n\n👤 کاربر: {user_id}\n📦 پلن: {plan_name}")
    del context.bot_data[f"pending_approve_{OWNER_ID}"]

async def reject_receipt(update, context):
    q = update.callback_query
    await q.answer()
    user_id = int(q.data.split("_")[1])
    kb = [[InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back_main")]]
    await context.bot.send_message(
        chat_id=user_id,
        text=f"❌ **رسید شما تایید نشد.**\n\n لطفاً با پشتیبانی تماس بگیرید.\n 💬 @{SUPPORT_USERNAME}\n━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )
    await q.edit_message_caption(caption=q.message.caption + "\n\n❌ **رد شد!**", parse_mode="Markdown")

# --- Main ---

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    logger.info(f"Starting Diaz Shop Bot... OWNER_ID={OWNER_ID}")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
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
    app.add_handler(CallbackQueryHandler(receipt_received, pattern="^receipt_(?!express_)"))
    app.add_handler(CallbackQueryHandler(receipt_express_received, pattern="^receipt_express_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text))

    logger.info("Bot is running! Waiting for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
