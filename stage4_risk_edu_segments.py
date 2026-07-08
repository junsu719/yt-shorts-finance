#!/usr/bin/env python3
"""Stage 4 — Add audio slice + subtitle slice to each clip → final 1920×1080 segment.

Reads:
  risk_education_segments/clip_XX.mp4    (raw video/chart from Stage 3)
  risk_education_segments/narration.mp3  (full narration audio)
  risk_education_segments/narration.srt  (full subtitle file)
  risk_education_segments/narration_charts.json

Overwrites each clip_XX.mp4 in-place with the fully assembled segment.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scripts.slot_allocator import build_slot_plan

OUT_DIR  = Path("/mnt/d/yt-shorts-finance/output/risk_education_segments")
NARR_MP3 = str(OUT_DIR / "narration.mp3")
NARR_SRT = str(OUT_DIR / "narration.srt")
CHARTS_P = str(OUT_DIR / "narration_charts.json")
SCRIPT_P = OUT_DIR / "script.json"

# ASS header for landscape 1920×1080
# Font size 48 ≈ 80 * (1080/1920) * 1.1 — readable at 1080p landscape
_ASS_HEADER = (
    "[Script Info]\n"
    "ScriptType: v4.00+\n"
    "PlayResX: 1920\n"
    "PlayResY: 1080\n"
    "WrapStyle: 2\n\n"
    "[V4+ Styles]\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
    "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
    "Alignment, MarginL, MarginR, MarginV, Encoding\n"
    "Style: Default,Noto Sans CJK TC,48,&H00FFFFFF,&H000000FF,"
    "&H00000000,&H80000000,1,0,0,0,100,100,0,0,3,3,1,2,60,60,50,1\n\n"
    "[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
)


# ── Time helpers ──────────────────────────────────────────────────────────────

def _ts_to_sec(ts: str) -> float:
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000


def _sec_to_ass(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600);  sec -= h * 3600
    m = int(sec // 60);    sec -= m * 60
    s = int(sec)
    cs = int((sec - s) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# ── SRT parsing ───────────────────────────────────────────────────────────────

def _parse_srt(path: str) -> list[tuple[float, float, str]]:
    entries: list[tuple[float, float, str]] = []
    blocks = re.split(r"\n\n+", Path(path).read_text(encoding="utf-8").strip())
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)", lines[1])
        if not m:
            continue
        entries.append((_ts_to_sec(m.group(1)), _ts_to_sec(m.group(2)),
                        "\n".join(lines[2:])))
    return entries


# ── ASS slice writer ──────────────────────────────────────────────────────────

def _write_ass_slice(
    entries: list[tuple[float, float, str]],
    t_start: float,
    t_end: float,
    out_path: str,
) -> int:
    """Write ASS file with entries overlapping [t_start, t_end], shifted to t=0.
    Returns number of dialogue lines written."""
    dialogues: list[str] = []
    for (es, ee, text) in entries:
        if ee <= t_start or es >= t_end:
            continue
        cs = max(es, t_start) - t_start
        ce = min(ee, t_end)   - t_start
        if ce - cs < 0.05:
            continue
        # Replace SRT newlines with ASS newline marker
        ass_text = r"\N".join(text.split("\n"))
        dialogues.append(
            f"Dialogue: 0,{_sec_to_ass(cs)},{_sec_to_ass(ce)},"
            f"Default,,0,0,0,,{ass_text}"
        )
    Path(out_path).write_text(
        _ASS_HEADER + "\n".join(dialogues) + "\n", encoding="utf-8"
    )
    return len(dialogues)


# ── FFmpeg helpers ────────────────────────────────────────────────────────────

def _ffmpeg(*args: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", *args],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _file_info(path: str) -> tuple[float, int]:
    r = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration,size",
         "-of", "default=noprint_wrappers=1", path],
        capture_output=True, text=True, check=True,
    )
    dur = size = 0.0
    for line in r.stdout.splitlines():
        if line.startswith("duration="):
            dur = float(line.split("=", 1)[1])
        elif line.startswith("size="):
            size = int(line.split("=", 1)[1])
    return dur, int(size)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    script         = json.loads(SCRIPT_P.read_text(encoding="utf-8"))
    search_queries = script.get("search_queries", [])
    slot_plan      = build_slot_plan(NARR_SRT, CHARTS_P, search_queries, "education")
    srt_entries    = _parse_srt(NARR_SRT)

    total = len(slot_plan)
    print(f"共 {total} 個 Slot，逐一合成 1920×1080 片段...\n")

    results: list[dict] = []

    for spec in slot_plan:
        bg_path = str(OUT_DIR / f"clip_{spec.index:02d}.mp4")
        label   = f"[{spec.index:02d}/{total}]"
        kind    = "CHART" if spec.type == "chart" else "video"

        # Temp files in /tmp (clean paths, no escaping issues in ass filter)
        aud_tmp = f"/tmp/_risk_aud_{spec.index:02d}.mp3"
        ass_tmp = f"/tmp/_risk_sub_{spec.index:02d}.ass"

        # Temp output in OUT_DIR for atomic rename
        with tempfile.NamedTemporaryFile(
            suffix=".mp4", dir=str(OUT_DIR), delete=False
        ) as tf:
            seg_tmp = tf.name

        try:
            # 1. Audio slice
            _ffmpeg(
                "-ss", str(spec.start),
                "-t",  str(spec.duration + 0.1),  # +0.1s to avoid tiny truncation
                "-i",  NARR_MP3,
                "-c",  "copy",
                aud_tmp,
            )

            # 2. Subtitle ASS slice
            n_subs = _write_ass_slice(srt_entries, spec.start, spec.end, ass_tmp)

            # 3. Assemble: burn subtitles when available
            # Escape colons in ASS path for FFmpeg filter (safe on /tmp/...)
            abs_ass = os.path.abspath(ass_tmp).replace(":", "\\:")
            vf_base = f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
            vf = vf_base + (f",ass='{abs_ass}'" if n_subs > 0 else "")

            _ffmpeg(
                "-i", bg_path,
                "-i", aud_tmp,
                "-vf", vf,
                "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                seg_tmp,
            )

            # 4. Atomic replace: raw clip → final segment
            os.replace(seg_tmp, bg_path)

            dur, size = _file_info(bg_path)
            print(f"  {label} {kind:5s}  {dur:.1f}s  {size//1024:6d} KB  "
                  f"subs={n_subs:2d}  clip_{spec.index:02d}.mp4")
            results.append({
                "slot": spec.index, "type": spec.type,
                "file": f"clip_{spec.index:02d}.mp4",
                "duration": round(dur, 2), "size": size, "subs": n_subs,
            })

        except Exception as e:
            print(f"  {label} ERROR: {e}")
            results.append({
                "slot": spec.index, "type": spec.type,
                "file": "ERROR", "duration": 0, "size": 0, "subs": 0,
            })
        finally:
            for p in (aud_tmp, ass_tmp):
                try: os.unlink(p)
                except FileNotFoundError: pass
            if os.path.exists(seg_tmp):
                os.unlink(seg_tmp)

    # ── Summary table ─────────────────────────────────────────────────────────
    print()
    print("=" * 68)
    print(f"  {'檔名':<20}  {'類型':<5}  {'時長':>6}  {'大小':>8}  {'字幕數':>5}")
    print("=" * 68)
    total_size = 0
    for r in results:
        if r["file"] == "ERROR":
            print(f"  clip_{r['slot']:02d}.mp4            ERROR")
            continue
        total_size += r["size"]
        print(
            f"  {r['file']:<20}  "
            f"{'CHART' if r['type']=='chart' else 'video':<5}  "
            f"{r['duration']:>5.1f}s  "
            f"{r['size']//1024:>6d} KB  "
            f"{r['subs']:>4d} 條"
        )
    print("=" * 68)
    ok = sum(1 for r in results if r["file"] != "ERROR")
    print(f"\n  完成：{ok}/{total}  |  總大小：{total_size / 1024 / 1024:.1f} MB")
    print(f"  輸出路徑：{OUT_DIR}")

    # Save summary for reference
    (OUT_DIR / "segments_summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
