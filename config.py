import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")

# Owner & Support
OWNER_IDS = [int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip()]
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "Xioqui_Xan")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "TechnicalSerena")
FSUB_LINK = os.getenv("FSUB_LINK", "https://t.me/TechnicalSerena")
FSUB_ID = os.getenv("FSUB_ID")  # can be None
LOG_CHANNEL = os.getenv("LOG_CHANNEL")  # optional
START_PIC = os.getenv("START_PIC")  # optional

# Limits
FREE_LIMIT = int(os.getenv("FREE_LIMIT", 3))
BASIC_LIMIT = int(os.getenv("BASIC_LIMIT", 15))
PREMIUM_LIMIT = int(os.getenv("PREMIUM_LIMIT", 50))

# Paths
DB_PATH = os.getenv("DB_PATH", "/tmp/serena_db/bot.db")
DL_DIR = os.getenv("DL_DIR", "/tmp/serena_dl")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(DL_DIR, exist_ok=True)

# Cookies (raw Netscape text from env)
YT_COOKIES = os.getenv("YT_COOKIES", "")
INSTAGRAM_COOKIES = os.getenv("INSTAGRAM_COOKIES", "")
TERABOX_COOKIES = os.getenv("TERABOX_COOKIES", "")

# Flask port
PORT = int(os.getenv("PORT", 10000))

# Max file size (2GB)
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
