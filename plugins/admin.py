from pyrogram import filters
from pyrogram.types import Message
from client import app
from database import (
    get_all_users, get_banned_users, get_total_users, get_premium_count,
    get_banned_count, ban_user, unban_user, set_plan, get_user
)
from utils.decorators import owner_only
from config import OWNER_IDS
import os
import sys
import asyncio

@app.on_message(filters.command("givepremium") & filters.private)
@owner_only
async def give_premium(client, message: Message):
    try:
        _, user_id, plan = message.text.split()
        user_id = int(user_id)
        days = 30 if plan.lower() == 'basic' else 365 if plan.lower() == 'premium' else None
        if not days:
            await message.reply_text("Plan must be 'basic' or 'premium'.")
            return
        await set_plan(user_id, plan.lower(), days)
        await message.reply_text(f"✅ {plan.capitalize()} plan given to {user_id} for {days} days.")
        try:
            await client.send_message(user_id, f"🎉 You have been granted **{plan.capitalize()}** plan for {days} days!")
        except:
            pass
    except:
        await message.reply_text("Usage: /givepremium <user_id> <basic/premium>")

@app.on_message(filters.command("removepremium") & filters.private)
@owner_only
async def remove_premium(client, message: Message):
    try:
        _, user_id = message.text.split()
        user_id = int(user_id)
        await set_plan(user_id, 'free')
        await message.reply_text(f"✅ {user_id} reverted to Free plan.")
        try:
            await client.send_message(user_id, "Your premium plan has expired/removed.")
        except:
            pass
    except:
        await message.reply_text("Usage: /removepremium <user_id>")

@app.on_message(filters.command("ban") & filters.private)
@owner_only
async def ban_cmd(client, message: Message):
    try:
        _, user_id = message.text.split()
        user_id = int(user_id)
        await ban_user(user_id)
        await message.reply_text(f"✅ Banned user {user_id}.")
        try:
            await client.send_message(user_id, "You have been banned from using this bot.")
        except:
            pass
    except:
        await message.reply_text("Usage: /ban <user_id>")

@app.on_message(filters.command("unban") & filters.private)
@owner_only
async def unban_cmd(client, message: Message):
    try:
        _, user_id = message.text.split()
        user_id = int(user_id)
        await unban_user(user_id)
        await message.reply_text(f"✅ Unbanned user {user_id}.")
        try:
            await client.send_message(user_id, "You have been unbanned. You can use the bot again.")
        except:
            pass
    except:
        await message.reply_text("Usage: /unban <user_id>")

@app.on_message(filters.command("stats") & filters.private)
@owner_only
async def stats_cmd(client, message: Message):
    total = await get_total_users()
    premium = await get_premium_count()
    banned = await get_banned_count()
    text = (
        f"**Bot Statistics**\n"
        f"Total Users: {total}\n"
        f"Premium: {premium}\n"
        f"Banned: {banned}"
    )
    await message.reply_text(text)

@app.on_message(filters.command("users") & filters.private)
@owner_only
async def users_cmd(client, message: Message):
    users = await get_all_users()
    if not users:
        await message.reply_text("No users.")
        return
    lines = ["**Users:**"]
    for u in users:
        lines.append(f"• {u['user_id']} (@{u['username']}) - {u['plan']} - Exp: {u['plan_expiry'] or 'Never'}")
    # Split if too long
    text = "\n".join(lines)
    if len(text) > 4096:
        with open("users.txt", "w") as f:
            f.write(text)
        await message.reply_document("users.txt")
        os.remove("users.txt")
    else:
        await message.reply_text(text)

@app.on_message(filters.command("banned") & filters.private)
@owner_only
async def banned_cmd(client, message: Message):
    users = await get_banned_users()
    if not users:
        await message.reply_text("No banned users.")
        return
    lines = ["**Banned Users:**"]
    for u in users:
        lines.append(f"• {u['user_id']} (@{u['username']})")
    await message.reply_text("\n".join(lines))

@app.on_message(filters.command("broadcast") & filters.private)
@owner_only
async def broadcast_cmd(client, message: Message):
    if message.reply_to_message:
        msg = message.reply_to_message
    elif len(message.command) >= 2:
        text = message.text.split(maxsplit=1)[1]
        msg = text
    else:
        await message.reply_text("Reply to a message or provide text.")
        return
    users = await get_all_users()
    sent = 0
    for u in users:
        try:
            if isinstance(msg, str):
                await client.send_message(u['user_id'], msg)
            else:
                await msg.copy(u['user_id'])
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.reply_text(f"Broadcast sent to {sent}/{len(users)} users.")

@app.on_message(filters.command("restart") & filters.private)
@owner_only
async def restart_cmd(client, message: Message):
    await message.reply_text("🔄 Restarting...")
    # os.execv to restart
    os.execv(sys.executable, ['python'] + sys.argv)
