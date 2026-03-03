from functools import wraps
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_user, create_user, get_daily_count
from utils.helpers import is_subscribed, is_owner, get_plan_limit
from config import OWNER_IDS, FSUB_LINK
import asyncio

def guard(func):
    """Decorator for user commands: ban check, force-sub, daily limit."""
    @wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        user_id = message.from_user.id
        # Ensure user in DB
        user = await get_user(user_id)
        if not user:
            await create_user(user_id, message.from_user.username or "", message.from_user.first_name)
            user = await get_user(user_id)

        # Ban check
        if user and user["is_banned"]:
            await message.reply_text("🚫 You are banned from using this bot.")
            return

        # Owner bypasses everything
        if is_owner(user_id):
            return await func(client, message, *args, **kwargs)

        # Force-sub check
        if not await is_subscribed(user_id):
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 Join Channel", url=FSUB_LINK),
                InlineKeyboardButton("🔄 Refresh", callback_data="check_sub")
            ]])
            await message.reply_text(
                "**⋆｡° ✮ °｡⋆\nYou must join our channel to use me!**",
                reply_markup=btn
            )
            return

        # Daily limit check
        daily = await get_daily_count(user_id)
        limit = get_plan_limit(user["plan"])
        if daily >= limit and user["plan"] != "premium":  # premium has high limit
            await message.reply_text(
                f"**❌ Daily download limit exceeded!**\n"
                f"You have used {daily}/{limit} downloads today.\n"
                f"Upgrade to Premium for more: /plans"
            )
            return

        return await func(client, message, *args, **kwargs)
    return wrapper

def owner_only(func):
    @wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        if not is_owner(message.from_user.id):
            await message.reply_text("🚫 Owner only command.")
            return
        return await func(client, message, *args, **kwargs)
    return wrapper
