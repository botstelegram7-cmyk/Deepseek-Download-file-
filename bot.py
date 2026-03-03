#!/usr/bin/env python3
import asyncio
import sys
import os
from client import app
from database import init_db
from web.app import start_flask
from utils.helpers import YT_COOKIES_FILE, INSTA_COOKIES_FILE, TERABOX_COOKIES_FILE
import logging

logging.basicConfig(level=logging.INFO)

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

async def main():
    # Initialize database
    await init_db()
    # Start Flask (keep-alive)
    start_flask()
    # Import plugins AFTER flask start but BEFORE app.start()
    # (they are already imported via plugins=root in client, but we need to ensure they are registered)
    # Actually, client.py already sets plugins=dict(root="plugins"), so they will be auto-loaded when app.start() is called.
    # We just need to start the bot.
    print("»»──── [ Starting Bot ] ────««")
    await app.start()
    print("✅ Bot is running. Press Ctrl+C to stop.")
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
