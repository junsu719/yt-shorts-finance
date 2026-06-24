import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

CUSTOM_DIR = Path(__file__).parent.parent / "assets" / "custom"
CUSTOM_DIR.mkdir(parents=True, exist_ok=True)


def get_image_size(path: str) -> tuple[int, int]:
    """Return (width, height) of an image via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-select_streams", "v:0", path],
        capture_output=True, text=True, check=True,
    )
    stream = json.loads(result.stdout)["streams"][0]
    return stream["width"], stream["height"]


def photo_to_clip(photo_path: str, output_path: str, duration: int = 5) -> tuple[int, int]:
    """Convert a custom photo to a 9:16 MP4 clip with Ken Burns zoom.

    Landscape / square photos (w/h > 9/16) get a blurred version of themselves
    as the background so no black bars appear.
    Portrait photos narrower than 9:16 get black padding.

    Returns (original_width, original_height).
    """
    w, h = get_image_size(photo_path)
    total_frames = duration * 30

    ken_burns = (
        f"zoompan=z='min(zoom+0.0006,1.15)'"
        f":x='iw/2-(iw/zoom/2)'"
        f":y='ih/2-(ih/zoom/2)'"
        f":d={total_frames}:s=1080x1920:fps=30"
    )

    if (w / h) > (9 / 16):
        # Landscape / square: blur-fill background + sharp centered foreground
        fc = (
            f"[0:v]split[a][b];"
            f"[a]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,boxblur=luma_radius=25:luma_power=3[bg];"
            f"[b]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,{ken_burns}[out]"
        )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", photo_path, "-t", str(duration),
            "-filter_complex", fc, "-map", "[out]",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an",
            output_path,
        ]
    else:
        # Narrow portrait: scale to fit, black padding, Ken Burns
        vf = (
            f"scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"{ken_burns}"
        )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", photo_path, "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an",
            output_path,
        ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return w, h
