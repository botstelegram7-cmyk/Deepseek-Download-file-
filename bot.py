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
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("pyrogram").setLevel(logging.DEBUG)
logging.getLogger("werkzeug").setLevel(logging.INFO)

# Initial delay before first connection attempt (seconds)
INITIAL_DELAY = 10

# Global flag to keep bot running
running = True
# Global flag to prevent multiple start attempts
_starting = False

def signal_handler():
    """Handle shutdown signals gracefully"""
    global running
    logging.info("Shutdown signal received, stopping bot...")
    running = False

async def start_bot_with_retry():
    """Start bot with initial delay and retry on FloodWait, handling already-connected case"""
    global _starting
    if _starting:
        logging.warning("Start already in progress, skipping...")
        return True
    _starting = True

    # Wait initial delay to avoid rapid restarts
    logging.info(f"⏳ Waiting {INITIAL_DELAY} seconds before connecting to Telegram...")
    await asyncio.sleep(INITIAL_DELAY)

    # If already connected, just return success
    if app.is_connected:
        logging.info("Client already connected, skipping start.")
        _starting = False
        return True

    retries = 5
    base_wait = 10
    for attempt in range(1, retries + 1):
        try:
            logging.info(f"»»──── [ Attempt {attempt} to start bot ] ────««")
            await app.start()
            logging.info("✅ Bot started successfully.")
            # Verify connection
            me = await app.get_me()
            logging.info(f"Logged in as: {me.first_name} (@{me.username})")
            _starting = False
            return True
        except FloodWait as e:
            wait_time = e.value
            logging.warning(f"⚠️ FloodWait: need to wait {wait_time} seconds.")
            if attempt < retries:
                logging.info(f"Retrying after {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logging.error("❌ Max retries reached. Exiting.")
                _starting = False
                return False
        except ConnectionError as e:
            if "already connected" in str(e).lower():
                logging.info("Client already connected (detected during start attempt). Treating as success.")
                _starting = False
                return True
            else:
                logging.error(f"❌ Connection error: {e}")
                if attempt < retries:
                    wait = base_wait * attempt
                    logging.info(f"Retrying in {wait} seconds...")
                    await asyncio.sleep(wait)
                else:
                    _starting = False
                    return False
        except Exception as e:
            logging.error(f"❌ Unexpected error during start: {e}", exc_info=True)
            if attempt < retries:
                wait = base_wait * attempt
                logging.info(f"Retrying in {wait} seconds...")
                await asyncio.sleep(wait)
            else:
                logging.error("❌ Max retries reached. Exiting.")
                _starting = False
                return False
    _starting = False
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

    logging.info("»»──── [ Starting Bot ] ────««")
    success = await start_bot_with_retry()
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
