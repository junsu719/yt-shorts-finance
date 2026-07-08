#!/usr/bin/env python3
"""Concatenate clip_01..clip_23 into risk_education_final.mp4 (no re-encode)."""
import subprocess
from pathlib import Path

OUT_DIR   = Path("/mnt/d/yt-shorts-finance/output/risk_education_segments")
LIST_FILE = OUT_DIR / "concat_list.txt"
FINAL     = OUT_DIR / "risk_education_final.mp4"

# Write concat list
lines = [f"file '{OUT_DIR}/clip_{i:02d}.mp4'" for i in range(1, 24)]
LIST_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"concat list: {len(lines)} clips")

# FFmpeg concat — -c copy: no re-encode, no quality loss, seamless join
print("正在合成...", flush=True)
subprocess.run(
    [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(LIST_FILE),
        "-c", "copy",
        str(FINAL),
    ],
    check=True,
)

# Report
result = subprocess.run(
    ["ffprobe", "-v", "error",
     "-show_entries", "format=duration,size",
     "-of", "default=noprint_wrappers=1", str(FINAL)],
    capture_output=True, text=True, check=True,
)
info = {}
for line in result.stdout.splitlines():
    k, v = line.split("=", 1)
    info[k] = v

dur  = float(info.get("duration", 0))
size = int(info.get("size", 0))
mins = int(dur // 60)
secs = dur % 60

print()
print("=" * 50)
print(f"  輸出：{FINAL}")
print(f"  總時長：{mins}分{secs:.1f}秒（{dur:.1f}s）")
print(f"  檔案大小：{size / 1024 / 1024:.1f} MB")
print("=" * 50)
