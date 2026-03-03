from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from client import app
from database import get_user, create_user, get_daily_count
from utils.helpers import is_owner, fmt_size
from config import OWNER_USERNAME, SUPPORT_USERNAME, FSUB_LINK, START_PIC, FREE_LIMIT, BASIC_LIMIT, PREMIUM_LIMIT
from utils.decorators import guard
import time

START_TIME = time.time()

@app.on_message(filters.command("start") & filters.private)
@guard
async def start_command(client, message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await create_user(user_id, message.from_user.username or "", message.from_user.first_name)
        user = await get_user(user_id)

    text = (
        "⋆｡° ✮ °｡⋆\n"
        "-ˏˋ⋆ ᴡ ᴇ ʟ ᴄ ᴏ ᴍ ᴇ ⋆ˊˎ-\n"
        "»»────── ✦ ──────««\n"
        f"Hello **{message.from_user.first_name}**!\n"
        "I can download media from **1000+ sources**.\n"
        "Send me any link to get started.\n\n"
        f"**Your Plan:** {user['plan'].capitalize()}\n"
        f"**Daily Used:** {await get_daily_count(user_id)} / {FREE_LIMIT if user['plan']=='free' else BASIC_LIMIT if user['plan']=='basic' else PREMIUM_LIMIT}\n"
        "»»───────────────««"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ Help", callback_data="help"),
         InlineKeyboardButton("📊 Stats", callback_data="stats"),
         InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("📜 Plans", callback_data="plans"),
         InlineKeyboardButton("📚 History", callback_data="history")],
        [InlineKeyboardButton("👤 Owner", url=f"https://t.me/{OWNER_USERNAME}"),
         InlineKeyboardButton("📢 Support", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ])
    if START_PIC:
        await message.reply_photo(photo=START_PIC, caption=text, reply_markup=buttons)
    else:
        await message.reply_text(text, reply_markup=buttons)

@app.on_callback_query()
async def callback_handler(client, cb: CallbackQuery):
    data = cb.data
    user_id = cb.from_user.id
    # Ensure user exists
    await create_user(user_id, cb.from_user.username or "", cb.from_user.first_name)

    if data == "check_sub":
        # Re-check subscription
        from utils.helpers import is_subscribed
        if await is_subscribed(user_id):
            await cb.answer("✅ Joined! Returning to start.", show_alert=False)
            await cb.message.delete()
            # Resend start message
            await start_command(client, cb.message)  # reuse, but need to pass a message object
            # Better to call send_home
            await send_home(client, user_id)
        else:
            await cb.answer("❌ You haven't joined yet!", show_alert=True)
    elif data == "home":
        await cb.message.delete()
        await send_home(client, user_id)
    elif data == "help":
        await show_help(cb)
    elif data == "plans":
        await show_plans(cb)
    elif data == "stats":
        await show_stats(cb, user_id)
    elif data == "history":
        await show_history(cb, user_id)
    elif data == "settings":
        await show_settings(cb, user_id)
    else:
        await cb.answer("Unknown action.")

async def send_home(client, user_id):
    # Fake a message object to reuse start_command
    class FakeMsg:
        def __init__(self, from_user, chat):
            self.from_user = from_user
            self.chat = chat
        async def reply_text(self, *args, **kwargs):
            pass
        async def reply_photo(self, *args, **kwargs):
            pass
    from pyrogram.types import User, Chat
    user = User(id=user_id, first_name="User", is_bot=False)
    chat = Chat(id=user_id, type="private")
    await start_command(client, FakeMsg(user, chat))

async def show_help(cb: CallbackQuery):
    text = (
        "»»──── [ Help ] ────««\n"
        "▸ /start - Welcome\n"
        "▸ /help - This menu\n"
        "▸ /audio <url> - Download audio only\n"
        "▸ /info <url> - Get media info\n"
        "▸ /mystats - Your usage\n"
        "▸ /history - Last 10 downloads\n"
        "▸ /queue - View your queue\n"
        "▸ /cancel - Cancel all downloads\n"
        "▸ /plans - Subscription plans\n"
        "▸ /feedback <msg> - Send feedback\n"
        "▸ /settings - Your settings\n"
        "»»───────────────««"
    )
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Home", callback_data="home")]])
    await cb.message.edit_text(text, reply_markup=buttons)

async def show_plans(cb: CallbackQuery):
    text = (
        "»»──── [ Plans ] ────««\n"
        "**🆓 Free**\n"
        f"▸ {FREE_LIMIT} downloads/day\n"
        "▸ Forever\n\n"
        "**🥉 Basic**\n"
        f"▸ {BASIC_LIMIT} downloads/day\n"
        "▸ 30 days\n\n"
        "**💎 Premium**\n"
        f"▸ {PREMIUM_LIMIT} downloads/day\n"
        "▸ 365 days\n\n"
        "Contact @Xioqui_Xan to upgrade."
    )
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Home", callback_data="home")]])
    await cb.message.edit_text(text, reply_markup=buttons)

async def show_stats(cb: CallbackQuery, user_id: int):
    from database import get_daily_count, get_user, get_user_downloads
    user = await get_user(user_id)
    daily = await get_daily_count(user_id)
    limit = FREE_LIMIT if user['plan']=='free' else BASIC_LIMIT if user['plan']=='basic' else PREMIUM_LIMIT
    used_bar = "●" * daily + "○" * (limit - daily) if daily <= limit else "●" * limit
    text = (
        "»»──── [ Your Stats ] ────««\n"
        f"**Plan:** {user['plan'].capitalize()}\n"
        f"**Daily usage:** {daily}/{limit}\n"
        f"[{used_bar}]\n"
        f"**Joined:** {user['joined_at'][:10]}\n"
        "»»───────────────««"
    )
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Home", callback_data="home")]])
    await cb.message.edit_text(text, reply_markup=buttons)

async def show_history(cb: CallbackQuery, user_id: int):
    from database import get_user_downloads
    downloads = await get_user_downloads(user_id, 10)
    if not downloads:
        text = "No downloads yet."
    else:
        lines = []
        for d in downloads:
            lines.append(f"▸ {d['title'][:30]}... ({d['created_at'][:10]})")
        text = "»»──── [ History ] ────««\n" + "\n".join(lines)
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Home", callback_data="home")]])
    await cb.message.edit_text(text, reply_markup=buttons)

async def show_settings(cb: CallbackQuery, user_id: int):
    from database import get_user
    user = await get_user(user_id)
    text = (
        "»»──── [ Settings ] ────««\n"
        f"**User ID:** `{user_id}`\n"
        f"**Plan:** {user['plan'].capitalize()}\n"
        f"**Expiry:** {user['plan_expiry'] or 'Never'}\n\n"
        "Use /feedback to contact owner."
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="stats"),
         InlineKeyboardButton("📚 History", callback_data="history")],
        [InlineKeyboardButton("🔙 Home", callback_data="home")]
    ])
    await cb.message.edit_text(text, reply_markup=buttons)

@app.on_message(filters.command("help") & filters.private)
@guard
async def help_command(client, message):
    await show_help(message)

@app.on_message(filters.command("plans") & filters.private)
@guard
async def plans_command(client, message):
    await show_plans(message)

@app.on_message(filters.command("mystats") & filters.private)
@guard
async def mystats_command(client, message):
    await show_stats(message, message.from_user.id)

@app.on_message(filters.command("history") & filters.private)
@guard
async def history_command(client, message):
    await show_history(message, message.from_user.id)

@app.on_message(filters.command("settings") & filters.private)
@guard
async def settings_command(client, message):
    await show_settings(message, message.from_user.id)

@app.on_message(filters.command("ping") & filters.private)
@guard
async def ping_command(client, message):
    start = time.time()
    msg = await message.reply_text("Pong!")
    end = time.time()
    await msg.edit_text(f"Pong! `{round((end-start)*1000)}ms`")

@app.on_message(filters.command("status") & filters.private)
@guard
async def status_command(client, message):
    from database import get_total_users, get_premium_count, get_banned_count
    total = await get_total_users()
    premium = await get_premium_count()
    banned = await get_banned_count()
    uptime = time.time() - START_TIME
    days = uptime // 86400
    hours = (uptime % 86400) // 3600
    minutes = (uptime % 3600) // 60
    text = (
        "»»──── [ Bot Status ] ────««\n"
        f"**Uptime:** {int(days)}d {int(hours)}h {int(minutes)}m\n"
        f"**Total users:** {total}\n"
        f"**Premium:** {premium}\n"
        f"**Banned:** {banned}\n"
        "»»───────────────««"
    )
    await message.reply_text(text)

@app.on_message(filters.command("feedback") & filters.private)
@guard
async def feedback_command(client, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /feedback <your message>")
        return
    text = message.text.split(maxsplit=1)[1]
    from database import add_feedback
    await add_feedback(message.from_user.id, text)
    await message.reply_text("✅ Feedback sent. Thank you!")
    # Forward to owner
    for owner in OWNER_IDS:
        try:
            await client.send_message(owner, f"📝 Feedback from {message.from_user.id}:\n{text}")
        except:
            pass
