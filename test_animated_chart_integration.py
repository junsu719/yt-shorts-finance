#!/usr/bin/env python3
"""
動畫圖表整合測試 — 跳過 TTS/影片下載，直接測試圖表生成 + 合成。
只需 ffmpeg、matplotlib，不需要 API 金鑰或網路。
"""

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from scripts.chart_gen import generate_animated_chart, CHART_TYPES
from scripts.assembler import concat_clips, assemble, make_fallback_clip


def make_silent_audio(path: str, duration: float = 10.0):
    """Generate a silent MP3 for testing without TTS."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono:d={duration}",
            "-c:a", "libmp3lame", "-b:a", "128k",
            path,
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def make_dummy_srt(path: str, duration: float = 10.0):
    """Write a minimal SRT file covering the audio duration."""
    mid = duration / 2
    content = (
        "1\n"
        "00:00:00,500 --> 00:00:03,000\n"
        "動畫圖表整合測試\n\n"
        f"2\n"
        f"00:00:{int(mid):02d},000 --> 00:00:{int(mid)+2:02d},000\n"
        "EPS趨勢動畫展示\n\n"
        f"3\n"
        f"00:00:{int(duration)-3:02d},000 --> 00:00:{int(duration)-1:02d},000\n"
        "本影片僅供教育用途，不構成投資建議\n\n"
    )
    Path(path).write_text(content, encoding="utf-8")


def main():
    run_id = int(time.time())
    work = Path(f"/mnt/d/yt-shorts-finance/output/{run_id}")
    work.mkdir(parents=True, exist_ok=True)
    print(f"\n=== 動畫圖表整合測試 ===")
    print(f"輸出目錄：{work}\n")

    chart_data = {
        "company": "測試公司",
        "currency": "NTD",
        "unit": "元",
        "quarters": ["22Q1", "22Q2", "22Q3", "22Q4", "23Q1", "23Q2", "23Q3", "23Q4"],
        "eps":          [2.1, 2.3, 2.5, 2.8, 3.1, 3.4, 3.8, 4.2],
        "revenue":      [210, 230, 250, 280, 310, 340, 380, 420],
        "gross_margin": [42.0, 43.5, 44.2, 45.1, 46.3, 47.2, 48.1, 49.5],
        "yoy_growth":   [-3.0, -1.5, 2.0, 6.5, 10.2, 14.8, 19.5, 25.0],
        "segments":     {"核心業務": 70, "新興業務": 30},
    }

    # ── Stage 1: 生成 2 個動畫圖表（eps_trend + gross_margin）─────────────────
    print("[圖表生成]")
    chart_configs = [
        ("eps_trend",    "vertical_bar_chart (EPS趨勢)", 6),
        ("gross_margin", "diverging_bar_chart (毛利率年增率)", 7),
    ]
    chart_clips = []
    for chart_type, desc, duration in chart_configs:
        clip_path = str(work / f"chart_{len(chart_clips)+1:02d}.mp4")
        print(f"  生成 {desc} → {Path(clip_path).name} ...", end="", flush=True)
        try:
            generate_animated_chart(chart_data, chart_type, clip_path, duration=duration)
            size_kb = os.path.getsize(clip_path) // 1024
            print(f" ✓ ({size_kb} KB)")
            chart_clips.append(clip_path)
        except Exception as e:
            print(f" ✗ {e}")
            return 1

    # ── Stage 2: 生成 5 個深色背景 fallback clip（代替影片素材）───────────────
    print("\n[背景素材] 使用深色 fallback 取代影片下載（測試模式）")
    video_clips = []
    for i in range(5):
        clip_path = str(work / f"video_{i+1:02d}.mp4")
        make_fallback_clip(clip_path, duration=5.0)
        video_clips.append(clip_path)
        print(f"  fallback clip {i+1}/5 ✓")

    # ── Stage 3: 按 earnings slot plan 排序：video chart video chart video video video
    slot_order = [
        video_clips[0],
        chart_clips[0],
        video_clips[1],
        chart_clips[1],
        video_clips[2],
        video_clips[3],
        video_clips[4],
    ]
    print(f"\n[Slot 配置] {len(slot_order)} 個 clips (2 chart + 5 video)")

    # ── Stage 4: 合成 background.mp4 ──────────────────────────────────────────
    print("\n[合成] 串接 clips → background.mp4 ...")
    bg_video = str(work / "background.mp4")
    concat_clips(slot_order, bg_video)
    bg_dur = _video_dur(bg_video)
    bg_kb = os.path.getsize(bg_video) // 1024
    print(f"  background.mp4: {bg_dur:.1f}s, {bg_kb} KB ✓")

    # ── Stage 5: 靜音音檔 + SRT ───────────────────────────────────────────────
    print("\n[音檔/字幕] 生成靜音 MP3 + 測試 SRT ...")
    audio_path = str(work / "narration.mp3")
    srt_path   = str(work / "narration.srt")
    make_silent_audio(audio_path, duration=10.0)
    make_dummy_srt(srt_path, duration=10.0)
    print("  narration.mp3: 10s 靜音 ✓")
    print("  narration.srt: 測試字幕 ✓")

    # ── Stage 6: 最終合成 ──────────────────────────────────────────────────────
    print("\n[最終合成] background + audio + subtitles → final.mp4 ...")
    final_path = str(work / "final.mp4")
    assemble(bg_video, audio_path, final_path, srt_path=srt_path)

    # ── 結果報告 ───────────────────────────────────────────────────────────────
    if os.path.exists(final_path):
        final_dur  = _video_dur(final_path)
        final_mb   = os.path.getsize(final_path) // (1024 * 1024)
        print(f"\n✓ 測試成功！")
        print(f"  輸出：{final_path}")
        print(f"  時長：{final_dur:.1f}s")
        print(f"  大小：{final_mb} MB")
        print(f"\n確認重點：")
        print(f"  1. chart_01.mp4 (eps_trend/vertical_bar) 已嵌入 final.mp4")
        print(f"  2. chart_02.mp4 (gross_margin/diverging_bar) 已嵌入 final.mp4")
        print(f"  3. 字幕正確燒錄")
        return 0
    else:
        print(f"\n✗ final.mp4 未生成！")
        return 1


def _video_dur(path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "v:0", path],
            capture_output=True, text=True, check=True,
        )
        return float(json.loads(r.stdout)["streams"][0]["duration"])
    except Exception:
        return 0.0


if __name__ == "__main__":
    sys.exit(main())
