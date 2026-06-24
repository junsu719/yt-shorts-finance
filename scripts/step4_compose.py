#!/usr/bin/env python3
"""
Interactive Step 4: 分段確認合成流程

用法：
    python scripts/step4_compose.py <output_dir>
    python scripts/step4_compose.py          # 自動選最新的輸出目錄

流程：
    小節一：背景素材確認   → 輸入「背景OK」
    小節二：字幕位置確認   → 輸入「字幕OK」
    小節三：段落長度確認   → 輸入「長度OK」
    小節四：完整合成
"""

import json
import math
import os
import subprocess
import sys
from pathlib import Path

# 讓同層的 assembler.py 可以被直接 import（無論從哪個目錄執行）
sys.path.insert(0, str(Path(__file__).parent))

# ── 專案固定路徑 ──────────────────────────────────────────────────────────────
BASE_DIR   = Path("/home/junsu/yt-shorts-finance")
AUDIO_PATH = BASE_DIR / "audio" / "narration.mp3"   # 全域音檔（固定）
CHARTS_DIR = BASE_DIR / "charts"
# 字幕（.srt）與 clip 存放在同一個 output/<timestamp>/ 資料夾，從 work_dir 取得


# ── ffprobe helpers ───────────────────────────────────────────────────────────

def _probe(path: str, select_streams: str = "v:0") -> dict:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", "-select_streams", select_streams, path,
            ],
            capture_output=True, text=True, check=True,
        )
        streams = json.loads(result.stdout).get("streams", [])
        return streams[0] if streams else {}
    except Exception:
        return {}


def _video_duration(path: str) -> float:
    info = _probe(path, "v:0")
    return float(info.get("duration", 0))


def _audio_duration(path: str) -> float:
    info = _probe(path, "a:0")
    return float(info.get("duration", 0))


def _is_valid_clip(path: str) -> bool:
    if not os.path.exists(path) or os.path.getsize(path) < 1024:
        return False
    return _video_duration(path) > 0.1


# ── Fallback clip ─────────────────────────────────────────────────────────────

def _make_fallback(output_path: str, duration: float = 5.0):
    """Dark solid background clip as fallback for missing/invalid slots."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=#0d1117:s=1080x1920:r=30:d={duration}",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", output_path,
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


# ── 小節一：背景素材確認 ──────────────────────────────────────────────────────

def step1_verify(work_dir: Path) -> list[str]:
    print("\n" + "=" * 60)
    print("【小節一：背景素材確認】")
    print("=" * 60)

    def _slot_num(p: Path) -> int | None:
        """clip_01.mp4 → 1，非數字格式 → None"""
        try:
            return int(p.stem.split("_")[1])
        except (IndexError, ValueError):
            return None

    all_clips = list(work_dir.glob("clip_*.mp4"))
    raw_clips = sorted(
        [p for p in all_clips if _slot_num(p) is not None and "_fallback" not in p.stem],
        key=lambda p: _slot_num(p),
    )

    if not raw_clips:
        print(f"  ⚠ 找不到任何 clip_01.mp4 格式的素材！")
        print(f"  搜尋路徑：{work_dir}")
        print(f"  目錄內容：{[p.name for p in all_clips] or '（空）'}")
        print()
        print("  請確認：")
        print("    1. 已執行過 Stage 1-3 產生素材")
        print("    2. 指定了正確的 output 資料夾（含時間戳，如 output/1778661212）")
        sys.exit(1)

    valid_paths: list[str] = []
    for clip in raw_clips:
        slot_num = _slot_num(clip)
        dur = _video_duration(str(clip))

        if dur > 0.1:
            size_kb = clip.stat().st_size // 1024
            print(f"  ✓ Slot {slot_num:02d}: {clip.name} ({dur:.1f}s, {size_kb}KB)")
            valid_paths.append(str(clip))
        else:
            fallback = str(work_dir / f"clip_{slot_num:02d}_fallback.mp4")
            print(f"  ✗ Slot {slot_num:02d}: {clip.name} — 無效，生成深色背景替代")
            _make_fallback(fallback, duration=5.0)
            print(f"    → 已生成 {Path(fallback).name}")
            valid_paths.append(fallback)

    print(f"\n  共 {len(valid_paths)} 個 Slot 確認完畢")
    print()
    while True:
        ans = input("確認無誤後輸入「背景OK」繼續（輸入「取消」結束）：").strip()
        if ans == "背景OK":
            break
        elif ans == "取消":
            print("已取消。")
            sys.exit(0)
        else:
            print("  請輸入「背景OK」繼續，或「取消」結束。")
    return valid_paths


# ── 小節二：字幕位置確認 ──────────────────────────────────────────────────────

def _wrap_cjk(text: str, max_px: int = 960) -> str:
    """Wrap subtitle text so each line fits within max_px virtual pixels.

    CJK characters are ~82px wide at FontSize 80; ASCII/punctuation ~44px.
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


def _srt_to_ass(srt_path: str, ass_path: str):
    """SRT → ASS with PlayResX=1080, PlayResY=1920 for correct centering."""
    import re

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


def step2_subtitle_preview(
    work_dir: Path,
    clip_paths: list[str],
    srt_path: str,
) -> str:
    print("\n" + "=" * 60)
    print("【小節二：字幕位置確認】")
    print("=" * 60)

    # SRT → ASS conversion（輸出至 work_dir，與 clip 同目錄）
    ass_path = str(work_dir / "narration_centered.ass")
    if os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
        _srt_to_ass(srt_path, ass_path)
        print("  ✓ SRT → ASS 轉換完成（PlayResX=1080, PlayResY=1920）")
        print("    字幕設定：FontSize=80, 置中對齊, MarginL/R=60, MarginV=80, 自動換行(960px)")

        subtitle_path = ass_path
    else:
        print("  ⚠ 找不到 SRT 字幕檔，跳過字幕")
        subtitle_path = srt_path

    # Generate preview screenshot at 5s (subtitle-rich moment)
    preview_path = str(work_dir / "subtitle_preview.png")
    ref_clip = clip_paths[0] if clip_paths else None

    if ref_clip and os.path.exists(ref_clip) and os.path.exists(ass_path):
        ref_dur = _video_duration(ref_clip)
        seek_time = min(3.0, ref_dur * 0.5)

        abs_ass = os.path.abspath(ass_path).replace("\\", "/").replace(":", "\\:")
        vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass='{abs_ass}'"

        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(seek_time), "-i", ref_clip,
                "-vframes", "1",
                "-vf", vf,
                "-q:v", "2", preview_path,
            ],
            capture_output=True,
        )
        if result.returncode == 0:
            print(f"  ✓ 預覽截圖：{preview_path}")
            print("    請用圖片查看器確認字幕置中、無偏移、無裁切")
        else:
            stderr_tail = result.stderr.decode(errors="ignore")[-300:]
            print(f"  ⚠ 截圖生成失敗：{stderr_tail}")
    else:
        print("  ⚠ 無法生成截圖（clip 或 ASS 檔案缺失）")

    print()
    while True:
        ans = input("確認字幕位置正確後輸入「字幕OK」繼續（輸入「取消」結束）：").strip()
        if ans == "字幕OK":
            break
        elif ans == "取消":
            print("已取消。")
            sys.exit(0)
        else:
            print("  請輸入「字幕OK」繼續，或「取消」結束。")
    return subtitle_path


# ── 小節三：段落長度確認 ──────────────────────────────────────────────────────

def step3_durations(clip_paths: list[str], audio_path: str) -> float:
    print("\n" + "=" * 60)
    print("【小節三：段落長度確認】")
    print("=" * 60)

    audio_dur = _audio_duration(audio_path)
    total_clip_dur = 0.0

    for i, clip in enumerate(clip_paths, 1):
        dur = _video_duration(clip)
        total_clip_dur += dur
        tag = "fallback" if "_fallback" in clip else "OK"
        print(f"  Slot {i:02d}: {Path(clip).name} → {dur:.2f}s  [{tag}]")

    repeat = math.ceil(audio_dur / total_clip_dur) + 1 if total_clip_dur > 0 else "?"
    print(f"\n  Clip 合計時長：{total_clip_dur:.2f}s")
    print(f"  音檔長度：     {audio_dur:.2f}s")
    print(f"  背景循環次數： {repeat} 次（確保影片覆蓋全程）")

    if total_clip_dur < 1.0:
        print("  ⚠ Clip 時長異常，無法繼續！")
        sys.exit(1)
    if audio_dur < 1.0:
        print("  ⚠ 音檔無效，無法繼續！")
        sys.exit(1)

    print()
    while True:
        ans = input("確認無誤後輸入「長度OK」繼續（輸入「取消」結束）：").strip()
        if ans == "長度OK":
            break
        elif ans == "取消":
            print("已取消。")
            sys.exit(0)
        else:
            print("  請輸入「長度OK」繼續，或「取消」結束。")
    return audio_dur


# ── 小節四：完整合成 ──────────────────────────────────────────────────────────

def step4_compose(
    work_dir: Path,
    clip_paths: list[str],
    audio_path: str,
    subtitle_path: str,
    audio_dur: float,
):
    print("\n" + "=" * 60)
    print("【小節四：完整合成】")
    print("=" * 60)

    from assembler import concat_clips, _tile_to_duration

    # 1. Concatenate clips (invalid ones already replaced in step1)
    bg_path = str(work_dir / "background.mp4")
    print(f"  串接 {len(clip_paths)} 個 clip → background.mp4 ...")
    concat_clips(clip_paths, bg_path)

    bg_dur = _video_duration(bg_path)
    print(f"  background.mp4 時長：{bg_dur:.1f}s")

    # 2. Tile background to cover audio duration
    duration = math.ceil(audio_dur)
    tiled_path = str(work_dir / "background_tiled.mp4")
    print(f"  循環背景至 {duration + 1}s → background_tiled.mp4 ...")
    _tile_to_duration(bg_path, tiled_path, duration + 1)

    # 3. Build vf filter
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if subtitle_path and os.path.exists(subtitle_path) and os.path.getsize(subtitle_path) > 0:
        abs_sub = os.path.abspath(subtitle_path).replace("\\", "/").replace(":", "\\:")
        if subtitle_path.endswith(".ass"):
            vf += f",ass='{abs_sub}'"
        else:
            vf += f",subtitles='{abs_sub}'"

    # 4. Final encode
    final_path = str(work_dir / "final.mp4")
    print(f"  最終編碼 → final.mp4 ...")

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", tiled_path,
            "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            final_path,
        ],
        capture_output=True,
        text=True,
    )

    if os.path.exists(tiled_path):
        os.remove(tiled_path)

    if result.returncode != 0:
        print(f"  ✗ FFmpeg 錯誤：\n{result.stderr[-800:]}")
        sys.exit(1)

    # 5. Preview screenshot at 10% mark
    preview_path = str(work_dir / "final_preview.png")
    seek_time = max(5.0, duration * 0.10)
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", str(seek_time),
            "-i", final_path, "-vframes", "1",
            "-q:v", "2", preview_path,
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    # Report
    final_dur = _video_duration(final_path)
    final_size = os.path.getsize(final_path) // (1024 * 1024)
    print(f"\n  ✓ 合成完成！")
    print(f"  輸出：{final_path}")
    print(f"  影片長度：{final_dur:.1f}s（音檔：{duration}s）")
    print(f"  檔案大小：{final_size}MB")
    print(f"  預覽截圖：{preview_path}")

    return final_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) >= 2:
        work_dir = Path(sys.argv[1])
    else:
        output_base = Path("/home/junsu/yt-shorts-finance/output")
        # 只選純數字名稱的資料夾（時間戳格式），取最大值（最新）
        ts_dirs = sorted(
            [d for d in output_base.iterdir() if d.is_dir() and d.name.isdigit()],
            key=lambda p: int(p.name),
            reverse=True,
        )
        if not ts_dirs:
            print("找不到任何時間戳資料夾（格式如 output/1778661212）")
            print("請指定路徑：python scripts/step4_compose.py <output_dir>")
            sys.exit(1)
        work_dir = ts_dirs[0]
        print(f"自動選擇最新輸出目錄：{work_dir}")

    if not work_dir.exists():
        print(f"目錄不存在：{work_dir}")
        sys.exit(1)

    audio_path = str(AUDIO_PATH)
    srt_path   = str(work_dir / "narration.srt")   # 字幕與 clip 同目錄

    if not AUDIO_PATH.exists():
        print(f"找不到音檔：{audio_path}")
        sys.exit(1)

    audio_dur_raw = _audio_duration(audio_path)
    srt_exists = os.path.exists(srt_path)
    print(f"\n工作目錄：{work_dir}")
    print(f"音檔：{audio_path} ({audio_dur_raw:.1f}s)")
    print(f"字幕：{srt_path} {'✓' if srt_exists else '⚠ 找不到，將跳過字幕'}")
    print(f"圖表：{CHARTS_DIR}")

    # 四個確認小節
    clip_paths = step1_verify(work_dir)
    subtitle_path = step2_subtitle_preview(work_dir, clip_paths, srt_path)
    audio_dur = step3_durations(clip_paths, audio_path)
    step4_compose(work_dir, clip_paths, audio_path, subtitle_path, audio_dur)


if __name__ == "__main__":
    main()
