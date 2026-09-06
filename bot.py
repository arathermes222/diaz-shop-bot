#!/usr/bin/env python3
"""Diaz Shop - Telegram Bot for VPN Config Sales"""

import os
import json
import time
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ─── Config ───────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@diazplaylist")
OWNER_ID = int(os.environ.get("OWNER_ID", "6326889425"))
SUPPORT_USERNAME = "MrArat"
CARD_NUMBER = "6219861825198608"
CARD_NAME = "امیرمحمد زارعی"
CONFIGS_FILE = "configs.json"
PENDING_FILE = "pending_state.json"
WALLET_FILE = "wallet.json"

# SpiderPanel settings
SPIDER_URL = os.environ.get("SPIDER_URL", "https://spiderpanel-production-2268.up.railway.app")
SPIDER_PASSWORD = os.environ.get("SPIDER_PASSWORD", "Arat")

CONFIG_PLANS = {
    "10gb": {"name": "۱۰ گیگ", "price": "۱۲,۰۰۰", "data": "10GB", "duration": "۱ ماه", "price_int": 12000, "limit_gb": 10, "days": 30},
    "20gb": {"name": "۲۰ گیگ", "price": "۳۰,۰۰۰", "data": "20GB", "duration": "۱ ماه", "price_int": 30000, "limit_gb": 20, "days": 30},
    "50gb": {"name": "۵۰ گیگ", "price": "۷۰,۰۰۰", "data": "50GB", "duration": "۱ ماه", "price_int": 70000, "limit_gb": 50, "days": 30},
    "80gb": {"name": "۸۰ گیگ", "price": "۱۱۰,۰۰۰", "data": "80GB", "duration": "۱ ماه", "price_int": 110000, "limit_gb": 80, "days": 30},
}

EXPRESS_PLANS = {
    "1m": {"name": "۱ ماهه", "price": "۲۲۰,۰۰۰", "price_int": 220000, "limit_gb": 0, "days": 30},
    "3m": {"name": "۳ ماهه", "price": "۳۳۰,۰۰۰", "price_int": 330000, "limit_gb": 0, "days": 90},
    "6m": {"name": "۶ ماهه", "price": "۴۹۰,۰۰۰", "price_int": 490000, "limit_gb": 0, "days": 180},
    "1y": {"name": "۱ ساله", "price": "۹۵۰,۰۰۰", "price_int": 950000, "limit_gb": 0, "days": 365},
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── SpiderPanel API ──────────────────────────────────────

class SpiderPanel:
    """Client for SpiderPanel API"""
    def __init__(self, base_url, password):
        self.base_url = base_url.rstrip("/")
        self.password = password
        self.session_token = None
        self.client = httpx.AsyncClient(timeout=30, verify=False)

    async def login(self):
        """Login and get session cookie"""
        try:
            r = await self.client.post(f"{self.base_url}/api/login", json={"password": self.password})
            if r.status_code == 200:
                # Extract session cookie
                for cookie in r.cookies.jar:
                    if cookie.name == "spider_session":
                        self.session_token = cookie.value
                        logger.info("SpiderPanel login OK")
                        return True
                # Try any cookie
                cookies = dict(r.cookies)
                if cookies:
                    self.session_token = list(cookies.values())[0]
                    logger.info(f"SpiderPanel login OK (cookie: {list(cookies.keys())[0]})")
                    return True
            logger.error(f"SpiderPanel login failed: {r.status_code} {r.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"SpiderPanel login error: {e}")
            return False

    def _headers(self):
        if self.session_token:
            # Try cookie-based auth
            return {}
        return {}

    def _cookies(self):
        if self.session_token:
            return {"spider_session": self.session_token}
        return {}

    async def _ensure_auth(self):
        if not self.session_token:
            await self.login()

    async def create_link(self, label, limit_gb=0, days=30, protocol="vless"):
        """Create a new config link"""
        await self._ensure_auth()
        try:
            body = {
                "label": label,
                "limit_value": limit_gb,
                "limit_unit": "GB",
                "expires_days": days,
                "protocol": protocol,
            }
            r = await self.client.post(
                f"{self.base_url}/api/links",
                json=body,
                cookies=self._cookies(),
            )
            if r.status_code == 200:
                data = r.json()
                logger.info(f"SpiderPanel link created: {data.get('uuid', '?')}")
                return data
            elif r.status_code == 401:
                # Re-login and retry
                self.session_token = None
                await self.login()
                r = await self.client.post(
                    f"{self.base_url}/api/links",
                    json=body,
                    cookies=self._cookies(),
                )
                if r.status_code == 200:
                    data = r.json()
                    logger.info(f"SpiderPanel link created (retry): {data.get('uuid', '?')}")
                    return data
            logger.error(f"SpiderPanel create_link failed: {r.status_code} {r.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"SpiderPanel create_link error: {e}")
            return None

    async def get_links(self):
        """Get all links with usage info"""
        await self._ensure_auth()
        try:
            r = await self.client.get(
                f"{self.base_url}/api/links",
                cookies=self._cookies(),
            )
            if r.status_code == 200:
                return r.json().get("links", [])
            elif r.status_code == 401:
                self.session_token = None
                await self.login()
                r = await self.client.get(
                    f"{self.base_url}/api/links",
                    cookies=self._cookies(),
                )
                if r.status_code == 200:
                    return r.json().get("links", [])
            logger.error(f"SpiderPanel get_links failed: {r.status_code}")
            return []
        except Exception as e:
            logger.error(f"SpiderPanel get_links error: {e}")
            return []

    async def get_link(self, uuid):
        """Get single link info"""
        links = await self.get_links()
        for link in links:
            if link.get("uuid") == uuid:
                return link
        return None

    async def close(self):
        await self.client.aclose()


# Global spider client
spider = SpiderPanel(SPIDER_URL, SPIDER_PASSWORD)

# ─── File Helpers ─────────────────────────────────────────

def _load(filename):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Load {filename} error: {e}")
    return {}

def _save(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Save {filename} error: {e}")

def load_pending(): return _load(PENDING_FILE)
def save_pending(d): _save(PENDING_FILE, d)
def load_configs(): return _load(CONFIGS_FILE)
def save_configs(d): _save(CONFIGS_FILE, d)
def load_wallet(): return _load(WALLET_FILE)
def save_wallet(d): _save(WALLET_FILE, d)

def get_balance(user_id):
    wallet = load_wallet()
    return wallet.get(str(user_id), {}).get("balance", 0)

def add_balance(user_id, amount):
    wallet = load_wallet()
    uid = str(user_id)
    if uid not in wallet:
        wallet[uid] = {"balance": 0, "history": []}
    wallet[uid]["balance"] += amount
    wallet[uid]["history"].append({"amount": amount, "type": "charge"})
    save_wallet(wallet)

def spend_balance(user_id, amount):
    wallet = load_wallet()
    uid = str(user_id)
    if uid not in wallet or wallet[uid]["balance"] < amount:
        return False
    wallet[uid]["balance"] -= amount
    wallet[uid]["history"].append({"amount": -amount, "type": "spend"})
    save_wallet(wallet)
    return True

async def is_member(chat_username, user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_username, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

def _bytes_to_human(n):
    """Convert bytes to human readable"""
    if n <= 0:
        return "نامحدود"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"

# ─── Main Menu ────────────────────────────────────────────

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
        [InlineKeyboardButton("💰 کیف پول", callback_data="wallet_menu")],
        [InlineKeyboardButton("👤 پنل کاربری", callback_data="user_panel")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ])

# ─── Start & Membership ───────────────────────────────────

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
    if not await is_member(CHANNEL_ID, query.from_user.id, context):
        await query.edit_message_text("❌ هنوز عضو کانال نشدید!\nاول عضو شوید و دوباره دکمه «عضو شدم» را بزنید.")
        return
    await query.message.delete()
    await send_welcome_msg(query.message)

async def send_welcome_msg(message_obj):
    await message_obj.reply_text(WELCOME_TEXT, reply_markup=main_menu_kb())

async def back_main(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(WELCOME_TEXT, reply_markup=main_menu_kb())

# ─── Wallet ───────────────────────────────────────────────

def wallet_text(user_id):
    bal = get_balance(user_id)
    return (
        f"💰 **کیف پول شما:**\n\n"
        f"💳 **موجودی:** {bal:,} تومان\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"موجودی خود را افزایش دهید و از آن برای خرید استفاده کنید."
    )

async def wallet_menu(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    kb = [
        [InlineKeyboardButton("💳 افزایش موجودی", callback_data="charge_wallet")],
        [InlineKeyboardButton("📊 تاریخچه تراکنش‌ها", callback_data="wallet_history")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    await q.edit_message_text(wallet_text(uid), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def charge_wallet(update, context):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton("۵۰,۰۰۰ تومان", callback_data="charge_50000")],
        [InlineKeyboardButton("۱۰۰,۰۰۰ تومان", callback_data="charge_100000")],
        [InlineKeyboardButton("۲۰۰,۰۰۰ تومان", callback_data="charge_200000")],
        [InlineKeyboardButton("۵۰۰,۰۰۰ تومان", callback_data="charge_500000")],
        [InlineKeyboardButton("📝 مبلغ دلخواه", callback_data="charge_custom")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet_menu")],
    ]
    await q.edit_message_text(
        "💳 **افزایش موجودی کیف پول**\n\n"
        "مبلغ مورد نظر را انتخاب کنید:\n\n"
        "━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def charge_custom(update, context):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    pending = load_pending()
    pending[uid] = {"waiting": True, "type": "charge_custom"}
    save_pending(pending)
    await q.edit_message_text(
        "📝 **مبلغ دلخواه را وارد کنید:**\n\n"
        "فقط عدد را تایپ کنید (مثال: 75000)\n\n"
        "━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def charge_amount(update, context):
    q = update.callback_query
    await q.answer()
    amount_str = q.data.replace("charge_", "")
    try:
        amount = int(amount_str)
    except ValueError:
        return
    kb = [
        [InlineKeyboardButton("📸 ارسال رسید", callback_data=f"charge_receipt_{amount}")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet_menu")],
    ]
    await q.edit_message_text(
        f"💳 **افزایش موجودی:** {amount:,} تومان\n\n"
        f"🏦 **شماره کارت:**\n`{CARD_NUMBER}`\n"
        f"👤 **به نام:** {CARD_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💰 مبلغ را به شماره کارت واریز کنید.\n"
        f"📸 سپس رسید پرداخت را ارسال کنید.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

async def charge_receipt_step(update, context):
    q = update.callback_query
    await q.answer()
    amount = int(q.data.replace("charge_receipt_", ""))
    uid = str(q.from_user.id)
    pending = load_pending()
    pending[uid] = {"waiting": True, "type": "charge", "amount": amount}
    save_pending(pending)
    await q.edit_message_text(
        f"📸 **لطفاً رسید پرداخت ({amount:,} تومان) را ارسال کنید:**\n\n"
        f"(عکس رسید را اینجا بفرستید)\n\n"
        f"━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

async def wallet_history(update, context):
    q = update.callback_query
    await q.answer()
    wallet = load_wallet()
    uid = str(q.from_user.id)
    user_wallet = wallet.get(uid, {})
    history = user_wallet.get("history", [])
    bal = user_wallet.get("balance", 0)

    if not history:
        text = "📊 **تاریخچه تراکنش‌ها:**\n\nهنوز تراکنشی ثبت نشده.\n\n━━━━━━━━━━━━━━━━━"
    else:
        text = f"📊 **تاریخچه تراکنش‌ها:**\n\n"
        for h in history[-10:]:
            sign = "+" if h["amount"] > 0 else ""
            text += f"{'💳' if h['type'] == 'charge' else '📦'} {sign}{h['amount']:,} تومان\n"
        text += f"\n━━━━━━━━━━━━━━━━━\n💰 **موجودی فعلی:** {bal:,} تومان"

    kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="wallet_menu")]]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ─── Config Purchase ──────────────────────────────────────

async def buy_config(update, context):
    q = update.callback_query
    await q.answer()
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
    uid = q.from_user.id
    bal = get_balance(uid)
    can_wallet = bal >= plan["price_int"]
    kb = []
    if can_wallet:
        kb.append([InlineKeyboardButton(f"💰 پرداخت از کیف پول ({plan['price']})", callback_data=f"pay_wallet_config_{pid}")])
    kb.append([InlineKeyboardButton("💳 پرداخت با کارت", callback_data=f"pay_config_{pid}")])
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="buy_config")])
    wallet_note = f"\n💰 موجودی کیف پول: {bal:,} تومان" if can_wallet else f"\n💰 موجودی کیف پول: {bal:,} تومان (نافicient)"
    await q.edit_message_text(
        f"📦 **پلن انتخابی:** {plan['name']}\n💰 **قیمت:** {plan['price']} تومان\n⏰ **مدت:** {plan['duration']}{wallet_note}\n\n━━━━━━━━━━━━━━━━━\n روش پرداخت را انتخاب کنید.",
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

# ─── Wallet Payment (auto-create config!) ─────────────────

async def pay_wallet_config(update, context):
    q = update.callback_query
    await q.answer()
    pid = q.data.replace("pay_wallet_config_", "")
    plan = CONFIG_PLANS.get(pid)
    if not plan:
        return
    uid = q.from_user.id
    price = plan["price_int"]

    if not spend_balance(uid, price):
        await q.edit_message_text("❌ موجودی کیف پول کافی نیست!",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 شارژ کیف پول", callback_data="charge_wallet")]]))
        return

    # Show loading
    await q.edit_message_text("⏳ **در حال ساخت کانفیگ...**\n\nلطفاً صبر کنید...", parse_mode="Markdown")

    # Create config on SpiderPanel automatically!
    label = f"Diaz-{uid}-{pid}"
    link_data = await spider.create_link(
        label=label,
        limit_gb=plan.get("limit_gb", 0),
        days=plan.get("days", 30),
        protocol="vless",
    )

    if link_data and link_data.get("vless_link"):
        config_link = link_data["vless_link"]
        uuid = link_data.get("uuid", "")

        # Save config locally
        configs = load_configs()
        uid_str = str(uid)
        if uid_str not in configs:
            configs[uid_str] = []
        configs[uid_str].append({
            "type": "کانفیگ", "data": plan["name"],
            "link": config_link, "spider_uuid": uuid,
            "usage": "جدید", "expiry": plan["duration"],
        })
        save_configs(configs)

        kb = [[InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back_main")]]
        await q.edit_message_text(
            f"✅ **کانفیگ شما آماده است!**\n\n"
            f"📦 **پلن:** {plan['name']}\n"
            f"💰 **مبلغ کسر شده:** {plan['price']} تومان\n\n"
            f"🔗 **لینک کانفیگ:**\n`{config_link}`\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"از خرید شما متشکریم! 🙏",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )
        logger.info(f"Auto config created for {uid}: {uuid}")
    else:
        # SpiderPanel failed, save pending for manual
        pending = load_pending()
        pending[str(uid)] = {"waiting": True, "plan": pid, "type": "config_wallet", "amount": price}
        save_pending(pending)

        kb = [[InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back_main")]]
        await q.edit_message_text(
            f"⏳ **سفارش شما ثبت شد!**\n\n"
            f"📦 **پلن:** {plan['name']}\n"
            f"💰 **مبلغ کسر شده:** {plan['price']} تومان\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"⚠️ ساخت خودکار کانفیگ ممکن نبود.\n"
            f"به زودی کانفیگ توسط پشتیبانی برایتان ارسال می‌شود!",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"⚠️ **ساخت خودکار کانفیگ ناموفق!**\n\n👤 کاربر: {uid}\n📦 پلن: {plan['name']}\n\nلطفاً دستی کانفیگ بفرستید."
        )

# ─── Express Purchase ─────────────────────────────────────

async def buy_express(update, context):
    q = update.callback_query
    await q.answer()
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
    uid = q.from_user.id
    bal = get_balance(uid)
    can_wallet = bal >= plan["price_int"]
    kb = []
    if can_wallet:
        kb.append([InlineKeyboardButton(f"💰 پرداخت از کیف پول ({plan['price']})", callback_data=f"pay_wallet_express_{pid}")])
    kb.append([InlineKeyboardButton("💳 پرداخت با کارت", callback_data=f"pay_express_{pid}")])
    kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="buy_express")])
    wallet_note = f"\n💰 موجودی کیف پول: {bal:,} تومان" if can_wallet else f"\n💰 موجودی کیف پول: {bal:,} تومان (نافicient)"
    await q.edit_message_text(
        f"🔐 **پلن انتخابی:** {plan['name']}\n💰 **قیمت:** {plan['price']} تومان\n{wallet_note}\n\n━━━━━━━━━━━━━━━━━\n روش پرداخت را انتخاب کنید.",
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

# ─── Wallet Payment for Express ───────────────────────────

async def pay_wallet_express(update, context):
    q = update.callback_query
    await q.answer()
    pid = q.data.replace("pay_wallet_express_", "")
    plan = EXPRESS_PLANS.get(pid)
    if not plan:
        return
    uid = q.from_user.id
    price = plan["price_int"]

    if not spend_balance(uid, price):
        await q.edit_message_text("❌ موجودی کیف پول کافی نیست!",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 شارژ کیف پول", callback_data="charge_wallet")]]))
        return

    pending = load_pending()
    pending[str(uid)] = {"waiting": True, "plan": pid, "type": "express_wallet", "amount": price}
    save_pending(pending)

    kb = [[InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back_main")]]
    await q.edit_message_text(
        f"✅ **پرداخت از کیف پول موفق!**\n\n"
        f"📦 **پلن:** {plan['name']}\n"
        f"💰 **مبلغ کسر شده:** {plan['price']} تومان\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"⏳ سفارش شما ثبت شد و به زودی اشتراک برایتان ارسال می‌شود!",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=(
            f"💰 **خرید ExpressVPN از کیف پول!**\n\n"
            f"👤 **کاربر:** {q.from_user.first_name} (@{q.from_user.username or 'ندارد'})\n"
            f"🆔 **آیدی:** {uid}\n"
            f"📦 **پلن:** {plan['name']}\n"
            f"💰 **مبلغ:** {plan['price']} تومان\n\n"
            f"لطفاً اشتراک ExpressVPN را برای کاربر ارسال کنید."
        ),
        parse_mode="Markdown"
    )

# ─── User Panel (with live SpiderPanel data) ──────────────

async def user_panel(update, context):
    q = update.callback_query
    await q.answer()
    uid = str(q.from_user.id)
    configs = load_configs()
    user_configs = configs.get(uid, [])
    bal = get_balance(int(uid))

    if not user_configs:
        text = (
            f"👤 **پنل کاربری:**\n\n"
            f"💰 **کیف پول:** {bal:,} تومان\n\n"
            f"📦 شما هنوز هیچ کانفیگی ندارید.\n"
            f"━━━━━━━━━━━━━━━━━"
        )
    else:
        text = f"👤 **پنل کاربری:**\n\n💰 **کیف پول:** {bal:,} تومان\n\n"

        # Try to get live data from SpiderPanel
        spider_links = {}
        try:
            links = await spider.get_links()
            for link in links:
                spider_links[link.get("uuid", "")] = link
        except Exception as e:
            logger.error(f"Failed to get SpiderPanel links: {e}")

        for i, cfg in enumerate(user_configs, 1):
            cfg_type = cfg.get('type', 'کانفیگ')
            cfg_data = cfg.get('data', '')
            cfg_link = cfg.get('link', '')
            spider_uuid = cfg.get('spider_uuid', '')

            # Get live usage from SpiderPanel
            if spider_uuid and spider_uuid in spider_links:
                sp = spider_links[spider_uuid]
                used = sp.get("used_bytes", 0)
                limit = sp.get("limit_bytes", 0)
                expired = sp.get("expired", False)
                if expired:
                    usage = "⏰ منقضی شده"
                elif limit > 0:
                    usage = f"{_bytes_to_human(used)} / {_bytes_to_human(limit)}"
                else:
                    usage = f"{_bytes_to_human(used)} / ∞"
            else:
                usage = cfg.get('usage', 'نامشخص')

            text += f"**{i}.** {cfg_type} - {cfg_data}\n"
            text += f"   📊 **حجم:** {usage}\n"
            text += f"   🔗 `{cfg_link}`\n\n"
        text += "━━━━━━━━━━━━━━━━━"

    kb = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="user_panel")],
        [InlineKeyboardButton("📦 خرید کانفیگ", callback_data="buy_config")],
        [InlineKeyboardButton("🔐 خرید ExpressVPN", callback_data="buy_express")],
        [InlineKeyboardButton("💰 کیف پول", callback_data="wallet_menu")],
        [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ─── Handle Receipt Photo ─────────────────────────────────

async def handle_photo(update, context):
    uid = str(update.effective_user.id)
    logger.info(f"PHOTO from {uid}")

    pending = load_pending()
    state = pending.get(uid)
    if not state or not state.get("waiting"):
        logger.info(f"No pending state for {uid}, ignoring")
        return

    logger.info(f"Processing receipt for {uid}: {state}")
    ptype = state.get("type", "config")
    user = update.effective_user

    # ─── Wallet charge receipt ───
    if ptype == "charge":
        amount = state.get("amount", 0)
        del pending[uid]
        save_pending(pending)

        caption = (
            f"💰 **رسید شارژ کیف پول!**\n\n"
            f"👤 **کاربر:** {user.first_name} (@{user.username or 'ندارد'})\n"
            f"🆔 **آیدی:** {user.id}\n"
            f"💰 **مبلغ:** {amount:,} تومان"
        )
        kb = [
            [InlineKeyboardButton("✅ تایید و شارژ کیف پول", callback_data=f"approve_charge_{user.id}_{amount}")],
            [InlineKeyboardButton("❌ رد", callback_data=f"reject_{user.id}")],
        ]
        try:
            await context.bot.send_photo(
                chat_id=OWNER_ID, photo=update.message.photo[-1].file_id,
                caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to forward charge receipt: {e}")

        kb2 = [[InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back_main")]]
        await update.message.reply_text(
            "✅ رسید شما دریافت شد!\n خیلی زود کیف پول شما شارژ می‌شه 😉\n━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup(kb2)
        )
        return

    # ─── Custom amount charge ───
    if ptype == "charge_custom":
        del pending[uid]
        save_pending(pending)
        await update.message.reply_text("❌ لطفاً ابتدا مبلغ را به صورت عدد تایپ کنید.")
        return

    # ─── Config / Express receipt ───
    plan_id = state.get("plan")
    plan = CONFIG_PLANS.get(plan_id) if ptype in ("config", "config_wallet") else EXPRESS_PLANS.get(plan_id)

    if not plan:
        logger.error(f"Plan not found: {ptype}/{plan_id}")
        return

    del pending[uid]
    save_pending(pending)

    caption = (
        f"📸 **رسید جدید!**\n\n"
        f"👤 **کاربر:** {user.first_name} (@{user.username or 'ندارد'})\n"
        f"🆔 **آیدی:** {user.id}\n"
        f"📦 **پلن:** {plan['name']}\n"
        f"💰 **مبلغ:** {plan['price']} تومان\n"
        f"📦 **نوع:** {'کانفیگ' if 'config' in ptype else 'ExpressVPN'}"
    )
    kb = [
        [InlineKeyboardButton("✅ تایید و ارسال", callback_data=f"approve_{ptype}_{user.id}_{plan_id}")],
        [InlineKeyboardButton("❌ رد", callback_data=f"reject_{user.id}")],
    ]

    try:
        await context.bot.send_photo(
            chat_id=OWNER_ID, photo=update.message.photo[-1].file_id,
            caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to forward receipt: {e}")

    kb2 = [[InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back_main")]]
    await update.message.reply_text(
        "✅ رسید شما دریافت شد!\n خیلی زود سفارشت پیگیری و تحویل داده میشه 😉\n━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(kb2)
    )

# ─── Admin: Approve Charge ────────────────────────────────

async def approve_charge(update, context):
    q = update.callback_query
    await q.answer()
    parts = q.data.split("_")
    user_id = int(parts[2])
    amount = int(parts[3])

    add_balance(user_id, amount)

    kb = [[InlineKeyboardButton("🏠 بازگشت به صفحه اصلی", callback_data="back_main")]]
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ **کیف پول شما شارژ شد!**\n\n💰 **مبلغ اضافه شده:** {amount:,} تومان\n\n━━━━━━━━━━━━━━━━━\nاز خرید شما متشکریم! 🙏",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )
    await q.edit_message_caption(caption=q.message.caption + "\n\n✅ **تایید و شارژ شد!**", parse_mode="Markdown")

# ─── Admin: Approve Config/Express Receipt ────────────────

async def approve_receipt(update, context):
    q = update.callback_query
    await q.answer()
    parts = q.data.split("_")
    ptype = parts[1]
    user_id = int(parts[2])
    plan_id = parts[3]

    if ptype == "charge":
        await approve_charge(update, context)
        return

    plan = CONFIG_PLANS.get(plan_id) if ptype in ("config", "config_wallet") else EXPRESS_PLANS.get(plan_id)
    plan_name = plan["name"] if plan else plan_id

    context.bot_data[f"pending_approve_{OWNER_ID}"] = {
        "user_id": user_id, "plan_type": ptype, "plan_id": plan_id, "plan_name": plan_name,
    }
    await q.edit_message_caption(
        caption=q.message.caption + "\n\n⏳ **در حال ارسال...**",
        parse_mode="Markdown"
    )
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"📝 **لطفاً لینک کانفیگ/اشتراک رو بفرست:**\n\n👤 **کاربر:** {user_id}\n📦 **پلن:** {plan_name}\n\nلینک رو تایپ کن و بفرست 👇",
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
    cfg_type = "کانفیگ" if "config" in plan_type else "ExpressVPN"
    configs[uid_str].append({
        "type": cfg_type, "data": plan_name,
        "link": config_link, "usage": "جدید", "expiry": "۱ ماه"
    })
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

# ─── Handle Custom Amount (text from user) ────────────────

async def handle_text(update, context):
    uid = str(update.effective_user.id)
    pending = load_pending()
    state = pending.get(uid)

    if state and state.get("type") == "charge_custom":
        try:
            amount = int(update.message.text.strip().replace(",", "").replace("،", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد صحیح وارد کنید.")
            return

        kb = [
            [InlineKeyboardButton("📸 ارسال رسید", callback_data=f"charge_receipt_{amount}")],
            [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet_menu")],
        ]
        await update.message.reply_text(
            f"💳 **افزایش موجودی:** {amount:,} تومان\n\n"
            f"🏦 **شماره کارت:**\n`{CARD_NUMBER}`\n"
            f"👤 **به نام:** {CARD_NAME}\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"💰 مبلغ را به شماره کارت واریز کنید.\n"
            f"📸 سپس رسید پرداخت را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )
        pending[uid]["amount"] = amount
        pending[uid]["type"] = "charge"
        save_pending(pending)
        return

    if update.effective_user.id == OWNER_ID:
        await handle_admin_text(update, context)

# ─── Main ─────────────────────────────────────────────────

async def post_init(application):
    """Login to SpiderPanel on startup"""
    logger.info("Logging in to SpiderPanel...")
    ok = await spider.login()
    if ok:
        logger.info("SpiderPanel connected! ✅")
    else:
        logger.warning("SpiderPanel login failed - auto-config will not work ⚠️")

async def post_shutdown(application):
    """Close SpiderPanel client"""
    await spider.close()

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    logger.info(f"Starting Diaz Shop Bot... OWNER_ID={OWNER_ID}")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()

    # Commands
    app.add_handler(CommandHandler("start", start))

    # Membership
    app.add_handler(CallbackQueryHandler(check_member, pattern="^check_member$"))

    # Config purchase
    app.add_handler(CallbackQueryHandler(buy_config, pattern="^buy_config$"))
    app.add_handler(CallbackQueryHandler(select_config, pattern="^config_"))
    app.add_handler(CallbackQueryHandler(pay_config, pattern="^pay_config_"))
    app.add_handler(CallbackQueryHandler(pay_wallet_config, pattern="^pay_wallet_config_"))
    app.add_handler(CallbackQueryHandler(receipt_received, pattern="^receipt_(?!express_)"))

    # Express purchase
    app.add_handler(CallbackQueryHandler(buy_express, pattern="^buy_express$"))
    app.add_handler(CallbackQueryHandler(select_express, pattern="^express_"))
    app.add_handler(CallbackQueryHandler(pay_express, pattern="^pay_express_"))
    app.add_handler(CallbackQueryHandler(pay_wallet_express, pattern="^pay_wallet_express_"))
    app.add_handler(CallbackQueryHandler(receipt_express_received, pattern="^receipt_express_"))

    # Wallet
    app.add_handler(CallbackQueryHandler(wallet_menu, pattern="^wallet_menu$"))
    app.add_handler(CallbackQueryHandler(charge_wallet, pattern="^charge_wallet$"))
    app.add_handler(CallbackQueryHandler(charge_custom, pattern="^charge_custom$"))
    app.add_handler(CallbackQueryHandler(charge_amount, pattern="^charge_[0-9]+$"))
    app.add_handler(CallbackQueryHandler(charge_receipt_step, pattern="^charge_receipt_"))
    app.add_handler(CallbackQueryHandler(wallet_history, pattern="^wallet_history$"))

    # User panel
    app.add_handler(CallbackQueryHandler(user_panel, pattern="^user_panel$"))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))

    # Admin
    app.add_handler(CallbackQueryHandler(approve_receipt, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_receipt, pattern="^reject_"))

    # Photos (receipts)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Text (custom amount or admin config link)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot is running! Waiting for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
