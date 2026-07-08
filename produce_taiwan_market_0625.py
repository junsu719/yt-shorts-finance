#!/usr/bin/env python3
"""
台股三日多空交戰 Shorts 製作腳本（2026-06-25）
題材：market | 1 diverging_bar 圖表 + 6 影片素材
"""
import json
import logging
import os
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from scripts.tts import synthesize
from scripts.video_gen import fetch_clip
from scripts.chart_gen import _anim_diverging_bar
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

# ── 旁白（Hook → 內容 → CTA → 警語）────────────────────────────────────────

NARRATION = (
    "台股這三天到底發生了什麼事？先跌一千七百點，今天又漲回來了！"
    "週二六月二十三日，台股盤中衝上四萬八千兩百一十八點歷史新高，"
    "但就在高點急轉直下。博通財報雖超預期，AI晶片業務成長卻不如市場的極高期待，"
    "外資開始大規模撤離，台股急跌六百四十點收場。"
    "週三更嚴峻！外資單日賣超一千七百七十四億元創歷史紀錄，"
    "費半大跌拖累台股，重挫一千零五十七點，寫下史上第八大單日跌幅，"
    "兩天合計跌近一千七百點。"
    "今天週四終於出現轉機。美光財報EPS暴增十二倍，"
    "證明AI記憶體需求是真實的，不是泡沫。"
    "市場情緒從恐慌轉為鬆一口氣，華邦電、南亞科漲超百分之八，"
    "帶動台股反彈二百一十一點。"
    "這場多空交戰，空方擔憂AI估值過高、外資大量出脫；"
    "多方則反擊基本面沒問題，週一開盤記得繼續觀察！"
    "追蹤頻道，每天盤後第一時間分析給你看！"
    "本影片僅供教育用途，不構成投資建議。"
)

# ── 圖表資料 ─────────────────────────────────────────────────────────────────

CHART_DATA = {
    "data":   [-640.0, -1057.0, 211.0],
    "labels": ["週二 6/23", "週三 6/24", "週四 6/25"],
    "title":  "台股三日漲跌點數",
    "unit":   "點",
    "duration": 7,
}

# ── 影片素材關鍵字（市場配置：1圖表＋6影片）──────────────────────────────────
# Slot 順序：video(pexels) | video(pixabay) | chart | video(mixkit)
#           | video(vecteezy) | video(pexels) | video(pixabay)

VIDEO_SLOTS = [
    {"source": "pexels",   "query": "stock market crash recovery"},
    {"source": "pixabay",  "query": "stock market volatility"},
    # slot 3 = chart（在下方插入）
    {"source": "mixkit",   "query": "stock market"},
    {"source": "vecteezy", "query": "stock market chart"},
    {"source": "pexels",   "query": "financial market volatility"},
    {"source": "pixabay",  "query": "bear bull market fight"},
]


def main():
    run_id = int(time.time())
    work = Path(f"/mnt/d/yt-shorts-finance/output/{run_id}")
    work.mkdir(parents=True, exist_ok=True)
    log.info(f"=== 台股三日多空交戰 Shorts 製作 ===")
    log.info(f"輸出目錄：{work}")

    # ── Stage 1: TTS + SRT ───────────────────────────────────────────────────
    log.info("[1/4] 語音合成...")
    audio_path = str(work / "narration.mp3")
    srt_path   = str(work / "narration.srt")
    duration   = synthesize(NARRATION, audio_path, srt_path=srt_path)
    char_count = len(NARRATION.replace(" ", "").replace("\n", ""))
    log.info(f"  字數：{char_count}字 | 時長：{duration:.1f}s")

    # ── Stage 2: 動畫圖表（diverging_bar）──────────────────────────────────
    log.info("[2/4] 生成動畫圖表...")
    chart_path = str(work / "chart_01.mp4")
    _anim_diverging_bar(
        data=CHART_DATA["data"],
        labels=CHART_DATA["labels"],
        title=CHART_DATA["title"],
        unit=CHART_DATA["unit"],
        output_path=chart_path,
        duration=CHART_DATA["duration"],
    )
    chart_kb = os.path.getsize(chart_path) // 1024
    log.info(f"  diverging_bar → chart_01.mp4 ({chart_kb} KB)")

    # ── Stage 3: 下載影片素材 ─────────────────────────────────────────────
    log.info("[3/4] 下載影片素材...")
    seen_ids:    set[str] = set()
    seen_hashes: set[str] = set()
    video_clips: list[str] = []

    for i, slot in enumerate(VIDEO_SLOTS, 1):
        clip_path = str(work / f"video_{i:02d}.mp4")
        src = slot["source"]
        q   = slot["query"]
        log.info(f"  Slot {i}/6 [{src}] '{q}'...")
        try:
            fetch_clip(q, clip_path, source=src,
                       seen_ids=seen_ids, seen_hashes=seen_hashes)
            log.info(f"    ✓")
        except Exception as e:
            log.warning(f"    [{src}] 失敗，嘗試 auto fallback: {e}")
            try:
                fetch_clip(q, clip_path, source="auto",
                           seen_ids=seen_ids, seen_hashes=seen_hashes)
                log.info(f"    ✓ (auto fallback)")
            except Exception as e2:
                log.error(f"    完全失敗，使用深色 fallback: {e2}")
                from scripts.assembler import make_fallback_clip
                make_fallback_clip(clip_path, duration=5.0)
        video_clips.append(clip_path)

    # ── 按市場 slot 順序排列（chart 插入第 3 位）──────────────────────────────
    clip_order = [
        video_clips[0],   # slot 1: pexels
        video_clips[1],   # slot 2: pixabay
        chart_path,        # slot 3: diverging_bar 圖表
        video_clips[2],   # slot 4: mixkit
        video_clips[3],   # slot 5: vecteezy
        video_clips[4],   # slot 6: pexels
        video_clips[5],   # slot 7: pixabay
    ]
    log.info(f"  素材共 {len(clip_order)} 個（圖表1 + 影片6）")

    # ── Stage 4: 合成 ─────────────────────────────────────────────────────
    log.info("[4/4] 合成最終影片...")
    bg_video = str(work / "background.mp4")
    concat_clips(clip_order, bg_video)

    final = str(work / "final.mp4")
    assemble(bg_video, audio_path, final, srt_path=srt_path)

    # ── 輸出報告 ──────────────────────────────────────────────────────────
    if os.path.exists(final):
        final_mb = os.path.getsize(final) // (1024 * 1024)
        log.info("=== 完成 ===")
        log.info(f"  輸出：{final}")
        log.info(f"  大小：{final_mb} MB | 時長：{duration:.1f}s")
        log.info(f"  標題：台股這三天為什麼多空交戰？")
        log.info(f"  標籤：#台股 #多空交戰 #記憶體 #美光 #Shorts")
        return 0
    else:
        log.error("final.mp4 未生成！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
