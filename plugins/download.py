import os
import asyncio
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from client import app
from database import increment_daily, add_download, get_user, get_daily_count, get_plan_limit
from utils.decorators import guard
from utils.helpers import is_url, extract_urls_from_text, get_download_path, cleanup_user_dir, fmt_size, is_owner
from downloader.core import download_direct, download_ytdlp, download_gdrive, download_m3u8, download_terabox_fallback
from downloader.media import remux_to_mp4, add_metadata, video_thumb, pdf_thumb, build_caption
from queue_manager import queue_manager
from config import LOG_CHANNEL, DL_DIR, MAX_FILE_SIZE
import time
import aiofiles

URL_PATTERN = filters.regex(r"https?://[^\s]+")

@app.on_message(filters.command("audio") & filters.private)
@guard
async def audio_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /audio <url>")
        return
    url = message.command[1]
    await process_download(message, url, audio_only=True)

@app.on_message(filters.command("info") & filters.private)
@guard
async def info_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /info <url>")
        return
    url = message.command[1]
    # Fetch info via yt-dlp without download
    import yt_dlp
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'N/A')
            uploader = info.get('uploader', 'N/A')
            duration = info.get('duration', 0)
            views = info.get('view_count', 0)
            text = (
                f"**Title:** {title}\n"
                f"**Uploader:** {uploader}\n"
                f"**Duration:** {duration}s\n"
                f"**Views:** {views}"
            )
            await message.reply_text(text)
        except Exception as e:
            await message.reply_text(f"Error: {e}")

@app.on_message(filters.private & filters.text & URL_PATTERN)
@guard
async def url_handler(client, message: Message):
    # Extract all URLs from message
    urls = extract_urls_from_text(message.text)
    if not urls:
        return
    # For simplicity, process first URL
    url = urls[0]
    await process_download(message, url, audio_only=False)

@app.on_message(filters.private & filters.document)
@guard
async def document_handler(client, message: Message):
    # Handle .txt file upload with URLs
    file = message.document
    if not file.file_name.endswith('.txt'):
        await message.reply_text("Please send a .txt file containing URLs.")
        return
    # Download file
    path = await message.download(file_name=get_download_path(message.from_user.id, "urls.txt"))
    async with aiofiles.open(path, 'r') as f:
        content = await f.read()
    urls = extract_urls_from_text(content)
    if not urls:
        await message.reply_text("No URLs found in file.")
        return
    # Queue all URLs? For now just process first.
    url = urls[0]
    await process_download(message, url, audio_only=False)

@app.on_message(filters.command("queue") & filters.private)
@guard
async def queue_command(client, message: Message):
    user_id = message.from_user.id
    # Show current queue
    if user_id not in queue_manager.queues or queue_manager.queues[user_id].empty():
        await message.reply_text("Your queue is empty.")
        return
    queue = queue_manager.queues[user_id]
    items = list(queue._queue)
    if queue_manager.current[user_id]:
        text = f"**Currently downloading:** {queue_manager.current[user_id][:50]}...\n\n"
    else:
        text = "**Queue:**\n"
    for i, (url, _) in enumerate(items, 1):
        text += f"{i}. {url[:50]}...\n"
    await message.reply_text(text)

@app.on_message(filters.command("cancel") & filters.private)
@guard
async def cancel_command(client, message: Message):
    user_id = message.from_user.id
    queue_manager.cancel_user(user_id)
    await message.reply_text("All your pending downloads have been cancelled.")

async def process_download(message: Message, url: str, audio_only: bool):
    user_id = message.from_user.id
    # Check size? We'll do after download.
    # Add to queue
    status_msg = await message.reply_text("⏳ Adding to queue...")
    await queue_manager.add(user_id, url, lambda: download_task(message, url, audio_only, status_msg))

async def download_task(msg: Message, url: str, audio_only: bool, status_msg: Message):
    user_id = msg.from_user.id
    start_time = time.time()
    dest_dir = get_download_path(user_id)
    # Determine file extension based on type? We'll let yt-dlp decide, but we need to preserve original.
    # We'll use a temporary filename and then determine final.
    temp_filename = f"temp_{int(start_time)}.%(ext)s"
    temp_path = os.path.join(dest_dir, temp_filename)
    try:
        # Download using appropriate method
        await status_msg.edit_text("⬇️ Downloading...")
        # Classify URL
        if 'drive.google.com' in url:
            final_path = await download_gdrive(url, temp_path.replace('%(ext)s', 'mp4'), status_msg, start_time)
        elif 'm3u8' in url or '.m3u8' in url:
            final_path = await download_m3u8(url, temp_path.replace('%(ext)s', 'mp4'), status_msg, start_time)
        else:
            # Use yt-dlp
            final_path = await download_ytdlp(url, temp_path, status_msg, start_time, extract_audio=audio_only)

        # If audio_only and we used yt-dlp, file might be .mp3 already.
        # Get actual file path
        if os.path.isdir(final_path):
            # yt-dlp might have created a file with different name
            files = os.listdir(dest_dir)
            final_path = max([os.path.join(dest_dir, f) for f in files], key=os.path.getctime)

        # Check size
        size = os.path.getsize(final_path)
        if size > MAX_FILE_SIZE:
            await status_msg.edit_text("❌ File too large (max 2GB).")
            return

        # For video, remux to MP4 if needed
        ext = final_path.split('.')[-1].lower()
        if not audio_only and ext in ('mkv', 'avi', 'mov', 'webm', 'flv', 'ts', 'wmv', 'm4v'):
            await status_msg.edit_text("🔄 Remuxing to MP4...")
            final_path = await remux_to_mp4(final_path)

        # Generate thumbnail
        thumb_path = None
        if ext in ('mp4', 'mkv', 'avi', 'mov', 'webm'):
            thumb_path = os.path.join(dest_dir, "thumb.jpg")
            thumb_path = await video_thumb(final_path, thumb_path)
        elif ext == 'pdf':
            thumb_path = os.path.join(dest_dir, "thumb.jpg")
            thumb_path = await pdf_thumb(final_path, thumb_path)

        # Build caption
        title = os.path.basename(final_path)
        caption = build_caption(title, size, url, msg.from_user.first_name, (await app.get_me()).first_name)

        # Upload
        await status_msg.edit_text("📤 Uploading...")
        sent = None
        if audio_only or ext in ('mp3', 'aac', 'flac', 'wav', 'm4a', 'opus'):
            sent = await msg.reply_audio(
                audio=final_path,
                caption=caption,
                title=title,
                performer="Serena Bot",
                thumb=thumb_path,
                progress=upload_progress,
                progress_args=(status_msg, start_time)
            )
        elif ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'):
            sent = await msg.reply_photo(
                photo=final_path,
                caption=caption,
                progress=upload_progress,
                progress_args=(status_msg, start_time)
            )
        elif ext == 'pdf':
            sent = await msg.reply_document(
                document=final_path,
                caption=caption,
                thumb=thumb_path,
                file_name=os.path.basename(final_path),
                progress=upload_progress,
                progress_args=(status_msg, start_time)
            )
        elif ext in ('mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'ts', 'wmv', 'm4v'):
            sent = await msg.reply_video(
                video=final_path,
                caption=caption,
                thumb=thumb_path,
                supports_streaming=True,
                progress=upload_progress,
                progress_args=(status_msg, start_time)
            )
        else:
            # Document for other extensions
            sent = await msg.reply_document(
                document=final_path,
                caption=caption,
                thumb=thumb_path,
                file_name=os.path.basename(final_path),
                progress=upload_progress,
                progress_args=(status_msg, start_time)
            )

        # Update database
        await increment_daily(user_id)
        await add_download(user_id, url, title, size, "done")
        await status_msg.delete()
        if LOG_CHANNEL:
            await app.send_message(LOG_CHANNEL, f"✅ Download: {user_id} - {title}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")
        await add_download(user_id, url, "Error", 0, "failed")
    finally:
        # Cleanup user directory after upload? We'll clean after a delay.
        asyncio.create_task(delayed_cleanup(user_id, 60))

async def delayed_cleanup(user_id, delay):
    await asyncio.sleep(delay)
    cleanup_user_dir(user_id)

async def upload_progress(current, total, message, start_time):
    from utils.progress import upload_progress as up
    await up(current, total, message, start_time)
