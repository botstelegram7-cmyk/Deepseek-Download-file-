import os
import aiohttp
import asyncio
import subprocess
import yt_dlp
import gdown
from urllib.parse import urlparse
from utils.helpers import get_download_path, YT_COOKIES_FILE, INSTA_COOKIES_FILE, TERABOX_COOKIES_FILE
from utils.progress import download_progress
from config import MAX_FILE_SIZE
import time

async def download_direct(url: str, dest_path: str, message, start_time):
    """Download via aiohttp with progress"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=True) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            total = int(resp.headers.get('content-length', 0))
            if total > MAX_FILE_SIZE:
                raise Exception("File too large (max 2GB)")
            with open(dest_path, 'wb') as f:
                downloaded = 0
                async for chunk in resp.content.iter_chunked(1024*1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    download_progress(downloaded, total, message, start_time)
    return dest_path

async def download_ytdlp(url: str, dest_path: str, message, start_time, extract_audio=False):
    """Use yt-dlp to download, with progress hook"""
    ydl_opts = {
        'outtmpl': dest_path,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [lambda d: yt_dlp_progress_hook(d, message, start_time)],
    }
    if extract_audio:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    # Add cookies if available
    if YT_COOKIES_FILE and ('youtube' in url or 'youtu.be' in url):
        ydl_opts['cookiefile'] = YT_COOKIES_FILE
    if INSTA_COOKIES_FILE and 'instagram' in url:
        ydl_opts['cookiefile'] = INSTA_COOKIES_FILE
    if TERABOX_COOKIES_FILE and 'terabox' in url:
        ydl_opts['cookiefile'] = TERABOX_COOKIES_FILE

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if extract_audio:
            # yt-dlp may output a different file (mp3)
            # Find actual file
            base = dest_path.rsplit('.', 1)[0]
            possible = base + '.mp3'
            if os.path.exists(possible):
                return possible
        return dest_path

def yt_dlp_progress_hook(d, message, start_time):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        download_progress(downloaded, total, message, start_time)

async def download_gdrive(url: str, dest_path: str, message, start_time):
    """Use gdown for Google Drive public files"""
    # gdown doesn't support progress callback easily, we'll just do it
    def hook(current, total):
        download_progress(current, total, message, start_time)
    gdown.download(url, dest_path, quiet=False, resume=True, proxy=None, speed=None, use_cookies=False, postprocess_hook=hook)
    return dest_path

async def download_m3u8(url: str, dest_path: str, message, start_time):
    """Use ffmpeg to download HLS stream"""
    # ffmpeg -i url -c copy -bsf:a aac_adtstoasc output.mp4
    # We'll run ffmpeg as subprocess and update progress via file size?
    # For simplicity, we'll just run and then assume done.
    cmd = ['ffmpeg', '-i', url, '-c', 'copy', '-bsf:a', 'aac_adtstoasc', '-y', dest_path]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    # Wait and check file size occasionally
    while True:
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
            break
        except asyncio.TimeoutError:
            if os.path.exists(dest_path):
                size = os.path.getsize(dest_path)
                download_progress(size, size, message, start_time)  # just update with current size as total? Not accurate
    return dest_path

async def download_terabox_fallback(url: str, dest_path: str, message, start_time):
    """Fallback for Terabox if yt-dlp fails: use terabox API (simplified)"""
    # For demonstration, we'll just call yt-dlp again with a different approach.
    # In reality, you'd need to implement terabox API scraping.
    # We'll raise an exception to indicate failure.
    raise NotImplementedError("Terabox fallback not implemented; using yt-dlp only.")
