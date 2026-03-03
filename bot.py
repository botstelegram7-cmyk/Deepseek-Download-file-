#!/usr/bin/env python3
import asyncio
import sys
import os
import time
from pyrogram.errors import FloodWait
from client import app
from database import init_db
from web.app import start_flask
from utils.helpers import YT_COOKIES_FILE, INSTA_COOKIES_FILE, TERABOX_COOKIES_FILE
import logging

logging.basicConfig(level=logging.INFO)

# Initial delay before first connection attempt (seconds)
# Helps prevent flood if bot restarts frequently
INITIAL_DELAY = 10

# Ensure cookies are written at startup (already done in helpers.py on import)
print("⚡ Serena Downloader Bot starting...")
print("╔════════════════════════════╗")
print("║   Serena Downloader Bot    ║")
print("║        ⋆｡°✮°｡⋆            ║")
print("╚════════════════════════════╝")
if YT_COOKIES_FILE:
    print(f"[COOKIES] YT_COOKIES -> wrote {YT_COOKIES_FILE}")
if INSTA_COOKIES_FILE:
    print(f"[COOKIES] INSTAGRAM_COOKIES -> wrote {INSTA_COOKIES_FILE}")
if TERABOX_COOKIES_FILE:
    print(f"[COOKIES] TERABOX_COOKIES -> wrote {TERABOX_COOKIES_FILE}")

async def start_bot_with_retry():
    """Start bot with initial delay and retry on FloodWait"""
    # Wait initial delay to avoid rapid restarts
    print(f"⏳ Waiting {INITIAL_DELAY} seconds before connecting to Telegram...")
    await asyncio.sleep(INITIAL_DELAY)

    retries = 5
    base_wait = 10
    for attempt in range(1, retries + 1):
        try:
            print(f"»»──── [ Attempt {attempt} to start bot ] ────««")
            await app.start()
            print("✅ Bot started successfully.")
            return True
        except FloodWait as e:
            wait_time = e.value  # seconds
            print(f"⚠️ FloodWait: need to wait {wait_time} seconds.")
            if attempt < retries:
                print(f"Retrying after {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                print("❌ Max retries reached. Exiting.")
                return False
        except Exception as e:
            print(f"❌ Unexpected error during start: {e}")
            if attempt < retries:
                wait = base_wait * attempt
                print(f"Retrying in {wait} seconds...")
                await asyncio.sleep(wait)
            else:
                print("❌ Max retries reached. Exiting.")
                return False
    return False

async def main():
    # Initialize database
    await init_db()
    # Start Flask (keep-alive)
    start_flask()
    print("»»──── [ Starting Bot ] ────««")
    success = await start_bot_with_retry()
    if not success:
        print("❌ Could not start bot. Exiting.")
        sys.exit(1)
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
