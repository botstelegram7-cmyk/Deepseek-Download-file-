import aiosqlite
import json
from datetime import datetime, timedelta
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                plan TEXT DEFAULT 'free',
                plan_expiry TEXT,
                daily_count INTEGER DEFAULT 0,
                last_reset TEXT,
                joined_at TEXT,
                is_banned INTEGER DEFAULT 0
            )
        """)
        # Downloads table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                url TEXT,
                title TEXT,
                file_size INTEGER,
                status TEXT,
                created_at TEXT
            )
        """)
        # Feedback table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT,
                created_at TEXT
            )
        """)
        await db.commit()

# ---------- User helpers ----------
async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def create_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.utcnow().isoformat()
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at, last_reset)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, full_name, now, now))
        await db.commit()

async def update_user(user_id: int, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        for key, value in kwargs.items():
            await db.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

async def reset_daily_if_needed(user_id: int):
    user = await get_user(user_id)
    if not user:
        return
    last = datetime.fromisoformat(user["last_reset"])
    now = datetime.utcnow()
    if now.date() > last.date():
        await update_user(user_id, daily_count=0, last_reset=now.isoformat())

async def increment_daily(user_id: int):
    await reset_daily_if_needed(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET daily_count = daily_count + 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_daily_count(user_id: int):
    await reset_daily_if_needed(user_id)
    user = await get_user(user_id)
    return user["daily_count"] if user else 0

# ---------- Plan helpers ----------
async def set_plan(user_id: int, plan: str, days: int = None):
    expiry = None
    if days:
        expiry = (datetime.utcnow() + timedelta(days=days)).isoformat()
    await update_user(user_id, plan=plan, plan_expiry=expiry)

async def check_plan_expiry():
    """Run periodically to expire plans"""
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.utcnow().isoformat()
        await db.execute("""
            UPDATE users SET plan='free', plan_expiry=NULL
            WHERE plan!='free' AND plan_expiry < ?
        """, (now,))
        await db.commit()

# ---------- Ban ----------
async def ban_user(user_id: int):
    await update_user(user_id, is_banned=1)

async def unban_user(user_id: int):
    await update_user(user_id, is_banned=0)

# ---------- Downloads log ----------
async def add_download(user_id: int, url: str, title: str, file_size: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.utcnow().isoformat()
        await db.execute("""
            INSERT INTO downloads (user_id, url, title, file_size, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, url, title, file_size, status, now))
        await db.commit()

async def get_user_downloads(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM downloads WHERE user_id = ? AND status = 'done'
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
        return await cursor.fetchall()

# ---------- Feedback ----------
async def add_feedback(user_id: int, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.utcnow().isoformat()
        await db.execute("INSERT INTO feedback (user_id, text, created_at) VALUES (?, ?, ?)",
                         (user_id, text, now))
        await db.commit()

# ---------- Stats ----------
async def get_total_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        return (await cursor.fetchone())[0]

async def get_premium_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE plan IN ('basic','premium')")
        return (await cursor.fetchone())[0]

async def get_banned_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
        return (await cursor.fetchone())[0]

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT user_id, username, plan, plan_expiry FROM users")
        return await cursor.fetchall()

async def get_banned_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT user_id, username FROM users WHERE is_banned=1")
        return await cursor.fetchall()
