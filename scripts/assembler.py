import json
import math
import os
import re
import subprocess
from pathlib import Path


def _audio_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", path],
        capture_output=True, text=True, check=True,
    )
    streams = json.loads(result.stdout)["streams"]
    return float(streams[0]["duration"])


def _video_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-select_streams", "v:0", path],
        capture_output=True, text=True, check=True,
    )
    streams = json.loads(result.stdout)["streams"]
    return float(streams[0]["duration"])


def _is_valid_clip(path: str) -> bool:
    """Return True if path exists, is non-empty, and has a readable video stream."""
    if not os.path.exists(path) or os.path.getsize(path) < 1024:
        return False
    try:
        dur = _video_duration(path)
        return dur > 0.1
    except Exception:
        return False


def make_fallback_clip(output_path: str, duration: float = 5.0):
    """Generate a dark solid background clip when a slot has no valid video."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=#0d1117:s=1080x1920:r=30:d={duration}",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", output_path,
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _wrap_cjk(text: str, max_px: int = 960) -> str:
    """Wrap subtitle text so each line fits within max_px virtual pixels.

    CJK characters are ~82px wide at FontSize 80; ASCII/punctuation ~44px.
    Preserves existing \\N breaks and inserts new ones where needed.
    Safe zone: MarginL=60 + MarginR=60 → available = 1080-120 = 960px.
    """
    def _char_px(c: str) -> int:
        cp = ord(c)
        if (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or
                0x3000 <= cp <= 0x303F or 0xFF00 <= cp <= 0xFFEF or
                0x20000 <= cp <= 0x2A6DF):
            return 82
        return 44

    segments = text.split(r"\N")
    out: list[str] = []
    for seg in segments:
        line, width = "", 0
        for ch in seg:
            cw = _char_px(ch)
            if width + cw > max_px and line:
                out.append(line)
                line, width = ch, cw
            else:
                line += ch
                width += cw
        if line:
            out.append(line)
    return r"\N".join(out)


def srt_to_ass(srt_path: str, ass_path: str):
    """Convert SRT to ASS with 1080×1920 play resolution for correct centering."""

    def _parse_ts(ts: str) -> float:
        h, m, rest = ts.split(":")
        s, ms = rest.replace(",", ".").split(".")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    def _ass_ts(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "WrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Noto Sans CJK TC,80,&H00FFFFFF,&H000000FF,"
        "&H00000000,&H80000000,1,0,0,0,100,100,0,0,3,3,1,2,60,60,80,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    srt_text = Path(srt_path).read_text(encoding="utf-8")
    blocks = re.split(r"\n\n+", srt_text.strip())
    dialogues: list[str] = []

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)", lines[1])
        if not m:
            continue
        start = _ass_ts(_parse_ts(m.group(1)))
        end = _ass_ts(_parse_ts(m.group(2)))
        text = _wrap_cjk(r"\N".join(lines[2:]))
        dialogues.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    Path(ass_path).write_text(header + "\n".join(dialogues) + "\n", encoding="utf-8")


def concat_clips(clip_paths: list[str], output_path: str):
    """Concat video clips; invalid clips are replaced with a dark fallback."""
    validated: list[str] = []
    for p in clip_paths:
        if _is_valid_clip(p):
            validated.append(p)
        else:
            fallback = p.replace(".mp4", "_fallback.mp4")
            make_fallback_clip(fallback, duration=5.0)
            validated.append(fallback)

    list_file = output_path + ".txt"
    with open(list_file, "w") as f:
        for p in validated:
            f.write(f"file '{os.path.abspath(p)}'\n")
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c", "copy",
                "-an", output_path,
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    finally:
        os.remove(list_file)


def _tile_to_duration(video_path: str, output_path: str, target_duration: float):
    """Repeat and re-encode video until it covers target_duration seconds."""
    vid_dur = _video_duration(video_path)
    repeats = math.ceil(target_duration / vid_dur) + 1

    list_file = output_path + ".txt"
    with open(list_file, "w") as f:
        for _ in range(repeats):
            f.write(f"file '{os.path.abspath(video_path)}'\n")
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-t", str(target_duration),
                "-c:v", "libx264", "-preset", "ultrafast",
                "-r", "30", "-g", "30",
                "-pix_fmt", "yuv420p",
                "-an", output_path,
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    finally:
        os.remove(list_file)


def assemble(video_path: str, audio_path: str, output_path: str, srt_path: str | None = None):
    """Combine background video with audio narration and optional burned-in subtitles."""
    duration = math.ceil(_audio_duration(audio_path))

    tiled = output_path + ".tiled.mp4"
    _tile_to_duration(video_path, tiled, duration + 1)

    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

    # Convert SRT → ASS so PlayResX/Y are 1080×1920, giving correct centering
    ass_path: str | None = None
    if srt_path and os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
        ass_path = srt_path.replace(".srt", ".ass")
        srt_to_ass(srt_path, ass_path)
        abs_ass = os.path.abspath(ass_path).replace("\\", "/").replace("'", "\\'").replace(":", "\\:")
        vf += f",ass='{abs_ass}'"

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", tiled,
                "-i", audio_path,
                "-map", "0:v", "-map", "1:a",
                "-vf", vf,
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                output_path,
            ],
            check=True,
        )
    finally:
        if os.path.exists(tiled):
            os.remove(tiled)
