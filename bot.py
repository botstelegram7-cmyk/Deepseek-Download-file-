#!/usr/bin/env python3
import asyncio
import sys
import os
import logging
import signal
from pyrogram.errors import FloodWait
from pyrogram import Client
from client import app
from database import init_db
from web.app import start_flask
from utils.helpers import YT_COOKIES_FILE, INSTA_COOKIES_FILE, TERABOX_COOKIES_FILE

# Set detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("pyrogram").setLevel(logging.INFO)
logging.getLogger("werkzeug").setLevel(logging.INFO)

# Initial delay before first connection attempt (seconds)
INITIAL_DELAY = 10

# Global flag to keep bot running
running = True

def signal_handler():
    """Handle shutdown signals gracefully"""
    global running
    logging.info("Shutdown signal received, stopping bot...")
    running = False

async def start_bot_once():
    """Start the bot once, handling FloodWait and already-connected cases."""
    # Wait initial delay to avoid rapid restarts
    logging.info(f"⏳ Waiting {INITIAL_DELAY} seconds before connecting to Telegram...")
    await asyncio.sleep(INITIAL_DELAY)

    # Check if already connected
    if app.is_connected:
        logging.info("Client already connected.")
        return True

    try:
        logging.info("»»──── [ Starting Bot ] ────««")
        await app.start()
        logging.info("✅ Bot started successfully.")
        # Verify connection
        me = await app.get_me()
        logging.info(f"Logged in as: {me.first_name} (@{me.username})")
        return True
    except FloodWait as e:
        wait_time = e.value
        logging.warning(f"⚠️ FloodWait: need to wait {wait_time} seconds.")
        logging.info(f"Will retry after {wait_time} seconds...")
        await asyncio.sleep(wait_time)
        # Retry once after flood wait
        try:
            await app.start()
            logging.info("✅ Bot started successfully after flood wait.")
            return True
        except Exception as e2:
            logging.error(f"❌ Failed to start after flood wait: {e2}", exc_info=True)
            return False
    except ConnectionError as e:
        if "already connected" in str(e).lower():
            logging.info("Client is already connected (start skipped).")
            return True
        else:
            logging.error(f"❌ Connection error: {e}")
            return False
    except Exception as e:
        logging.error(f"❌ Unexpected error during start: {e}", exc_info=True)
        return False

async def main():
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Initialize database
    await init_db()
    logging.info("Database initialized.")

    # Start Flask (keep-alive) in a separate thread
    start_flask()
    logging.info("Flask keep-alive server started.")

    # Start bot
    success = await start_bot_once()
    if not success:
        logging.error("❌ Could not start bot. Exiting.")
        sys.exit(1)

    logging.info("✅ Bot is now running and waiting for updates...")

    # Keep the bot alive indefinitely
    try:
        while running:
            await asyncio.sleep(1)  # short sleep to remain responsive to signals
    except asyncio.CancelledError:
        pass
    finally:
        logging.info("Stopping bot...")
        if app.is_connected:
            await app.stop()
        logging.info("Bot stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received.")
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
