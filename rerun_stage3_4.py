"""Rerun Stage 3 + 4 for an existing output folder with new clip queries.

Usage:
    python rerun_stage3_4.py <run_id>

Reads narration.mp3 and narration.srt from the existing folder,
downloads fresh clips using the hardcoded queries below, then
re-assembles final.mp4 in the same folder.
"""
import json
import logging
import sys
from pathlib import Path

from scripts.video_gen import fetch_clip
from scripts.image_gen import generate_image, image_to_clip
from scripts.assembler import concat_clips, assemble

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── 指定查詢（依 slot 分配：奇數 slot → Pexels，偶數 slot → Pixabay）──────
PEXELS_QUERIES = [
    "stock market",
    "computer chip technology",
    "server data center",
    "business finance chart",
    "trading floor",
]
PIXABAY_QUERIES = [
    "stock market trading",
    "semiconductor chip",
    "Taiwan technology",
    "data center server",
    "stock chart rising",
]

CLIPS_TO_GENERATE = 5


def rerun(run_id: str) -> str:
    work = Path(f"/mnt/d/yt-shorts-finance/output/{run_id}")
    if not work.exists():
        sys.exit(f"找不到資料夾：{work}")

    audio_path = str(work / "narration.mp3")
    srt_path = str(work / "narration.srt")
    if not Path(audio_path).exists():
        sys.exit("找不到 narration.mp3，請確認 run_id 正確")

    log.info(f"=== 重跑 Stage 3+4：{run_id} ===")

    # Stage 3 — download clips with specified queries
    log.info("[3/4] 下載背景影片（使用指定關鍵字）...")
    clip_paths = []
    seen_ids: set[str] = set()
    pexels_idx = 0
    pixabay_idx = 0

    for slot in range(CLIPS_TO_GENERATE):
        clip_path = str(work / f"clip_{slot+1:02d}.mp4")
        use_pexels = (slot % 2 == 0)  # slots 0,2,4 → Pexels; slots 1,3 → Pixabay

        if use_pexels:
            q = PEXELS_QUERIES[pexels_idx % len(PEXELS_QUERIES)]
            fetch_clip(q, clip_path, source="pexels", seen_ids=seen_ids)
            log.info(f"  Slot {slot+1}/{CLIPS_TO_GENERATE}: [pexels] query='{q}'")
            pexels_idx += 1
        else:
            q = PIXABAY_QUERIES[pixabay_idx % len(PIXABAY_QUERIES)]
            fetch_clip(q, clip_path, source="pixabay", seen_ids=seen_ids)
            log.info(f"  Slot {slot+1}/{CLIPS_TO_GENERATE}: [pixabay] query='{q}'")
            pixabay_idx += 1

        clip_paths.append(clip_path)

    # Rebuild background
    bg_video = str(work / "background.mp4")
    concat_clips(clip_paths, bg_video)

    # Stage 4 — assemble
    log.info("[4/4] 合成最終影片...")
    final = str(work / "final.mp4")
    assemble(bg_video, audio_path, final, srt_path=srt_path)

    log.info(f"=== 完成 ===")
    log.info(f"  輸出：{final}")
    return final


if __name__ == "__main__":
    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not run_id:
        sys.exit("用法：python rerun_stage3_4.py <run_id>")
    rerun(run_id)
