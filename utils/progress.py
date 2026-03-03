import time
from utils.helpers import fmt_size

def progress_bar(current, total, bar_length=10):
    fraction = current / total if total else 0
    arrow = int(fraction * bar_length)
    bar = "●" * arrow + "○" * (bar_length - arrow)
    percent = int(fraction * 100)
    return f"[{bar}] {percent}%"

async def upload_progress(current, total, message, start_time):
    """Callback for pyrogram uploads"""
    now = time.time()
    if now - getattr(upload_progress, "last_update", 0) < 2:
        return
    upload_progress.last_update = now
    speed = current / (now - start_time) if now - start_time else 0
    eta = (total - current) / speed if speed else 0
    text = (
        f"**Uploading...**\n"
        f"{progress_bar(current, total)}\n"
        f"**Size:** {fmt_size(current)} / {fmt_size(total)}\n"
        f"**Speed:** {fmt_size(speed)}/s\n"
        f"**ETA:** {fmt_time(eta)}"
    )
    try:
        await message.edit_text(text)
    except:
        pass

def download_progress(current, total, message, start_time):
    """Callback for aiohttp/yt-dlp downloads (sync)"""
    # For simplicity we use a global variable to track last update
    if not hasattr(download_progress, "last_update"):
        download_progress.last_update = 0
    now = time.time()
    if now - download_progress.last_update < 2:
        return
    download_progress.last_update = now
    speed = current / (now - start_time) if now - start_time else 0
    eta = (total - current) / speed if speed else 0
    text = (
        f"**Downloading...**\n"
        f"{progress_bar(current, total)}\n"
        f"**Size:** {fmt_size(current)} / {fmt_size(total)}\n"
        f"**Speed:** {fmt_size(speed)}/s\n"
        f"**ETA:** {fmt_time(eta)}"
    )
    # We'll use asyncio to edit message, but this callback is sync.
    # We'll handle it by storing message and updating via loop.call_soon_threadsafe.
    import asyncio
    asyncio.get_running_loop().call_soon_threadsafe(
        lambda: asyncio.create_task(message.edit_text(text))
    )
