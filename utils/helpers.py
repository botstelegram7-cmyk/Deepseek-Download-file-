import re
import os
import shutil
from datetime import datetime
from pyrogram.types import Message
from config import OWNER_IDS, FSUB_ID, SUPPORT_USERNAME, FSUB_LINK
from client import app

def fmt_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name)-1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

def fmt_time(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}h {m}m {s}s"
    elif m:
        return f"{m}m {s}s"
    else:
        return f"{s}s"

def fmt_dt(iso_str):
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%Y-%m-%d %H:%M")

def is_url(text: str):
    regex = r"https?://[^\s]+"
    return re.match(regex, text)

def extract_urls_from_text(text: str):
    return re.findall(r"https?://[^\s]+", text)

async def is_subscribed(user_id: int):
    if not FSUB_ID:
        return True  # force-sub disabled
    try:
        member = await app.get_chat_member(FSUB_ID, user_id)
        # member.status is ChatMemberStatus enum, convert to string
        status = str(member.status).lower()
        return status in ("member", "administrator", "creator")
    except:
        return False

def is_owner(user_id: int):
    return user_id in OWNER_IDS

def get_plan_limit(plan: str):
    from config import FREE_LIMIT, BASIC_LIMIT, PREMIUM_LIMIT
    if plan == "basic":
        return BASIC_LIMIT
    elif plan == "premium":
        return PREMIUM_LIMIT
    else:
        return FREE_LIMIT

def cleanup_user_dir(user_id: int):
    path = os.path.join(os.getenv("DL_DIR", "/tmp/serena_dl"), str(user_id))
    if os.path.exists(path):
        shutil.rmtree(path)

def get_download_path(user_id: int, filename: str = ""):
    user_dir = os.path.join(os.getenv("DL_DIR", "/tmp/serena_dl"), str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, filename) if filename else user_dir

def write_cookies(env_var: str, name: str):
    """Write raw Netscape cookies to /tmp/cookie_{name}.txt if valid"""
    raw = env_var.strip()
    if raw and (raw.startswith("# Netscape") or "\t" in raw):
        path = f"/tmp/cookie_{name}.txt"
        with open(path, "w") as f:
            f.write(raw)
        return path
    return None

# Initialize cookies at startup
YT_COOKIES_FILE = write_cookies(os.getenv("YT_COOKIES", ""), "yt_cookies")
INSTA_COOKIES_FILE = write_cookies(os.getenv("INSTAGRAM_COOKIES", ""), "insta_cookies")
TERABOX_COOKIES_FILE = write_cookies(os.getenv("TERABOX_COOKIES", ""), "terabox_cookies")
