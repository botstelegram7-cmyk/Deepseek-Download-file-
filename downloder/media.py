import os
import subprocess
import asyncio
from PIL import Image
import fitz  # PyMuPDF
from utils.helpers import fmt_size

async def remux_to_mp4(input_path: str) -> str:
    """Remux video to MP4 (H.264/AAC) for Telegram streaming"""
    output = input_path.rsplit('.', 1)[0] + '_remux.mp4'
    # Use ffmpeg to re-encode if needed, but we can try copy if codecs compatible
    # For simplicity, we'll always re-encode to H.264/AAC
    cmd = [
        'ffmpeg', '-i', input_path,
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        '-movflags', '+faststart', '-y', output
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await proc.wait()
    if os.path.exists(output) and os.path.getsize(output) > 0:
        return output
    return input_path  # fallback

async def add_metadata(file_path: str, title: str, artist: str = "", comment: str = ""):
    """Inject metadata into audio/video using ffmpeg"""
    # For video, we set metadata; for audio we can set ID3 tags.
    # This is a simplified version; might need more sophisticated handling.
    ext = file_path.split('.')[-1].lower()
    if ext in ('mp3', 'm4a', 'aac'):
        # Use ffmpeg to add metadata
        temp = file_path + '.tmp'
        cmd = ['ffmpeg', '-i', file_path, '-metadata', f'title={title}',
               '-metadata', f'artist={artist}', '-metadata', f'comment={comment}',
               '-c', 'copy', '-y', temp]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        if os.path.exists(temp):
            os.replace(temp, file_path)
    # For video, we can add metadata but it's less critical.

async def video_thumb(input_path: str, output_path: str, seek_times=[3,1,10,30,0.1]):
    """Extract thumbnail from video using ffmpeg, trying multiple seek positions"""
    for seek in seek_times:
        cmd = [
            'ffmpeg', '-ss', str(seek), '-i', input_path,
            '-vframes', '1', '-vf', 'scale=320:-1', '-y', output_path
        ]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.wait()
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
    return None

async def pdf_thumb(input_path: str, output_path: str):
    """Generate thumbnail from first page of PDF using PyMuPDF"""
    try:
        doc = fitz.open(input_path)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom
        pix.save(output_path)
        doc.close()
        return output_path
    except:
        return None

def build_caption(title: str, size: int, url: str, user_name: str, bot_name: str) -> str:
    """Build formatted caption for uploaded file"""
    return (
        f"**»»──── ««**\n"
        f"**📁 {title}**\n"
        f"**📦 Size:** {fmt_size(size)}\n"
        f"**🔗 Source:** {url[:50]}...\n"
        f"**👤 Requested by:** {user_name}\n"
        f"**🤖 Bot:** {bot_name}\n"
        f"**»»────────── ««**"
    )
