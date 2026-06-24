"""Step 4：合成最終影片並輸出預覽截圖（moviepy）"""

from pathlib import Path


def _find_cjk_font() -> str:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return "DejaVu-Sans"


BASE_DIR   = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
CHARTS_DIR = BASE_DIR / "charts"
ASSETS_DIR = BASE_DIR / "assets"
AUDIO_DIR  = BASE_DIR / "audio"

DISCLAIMER = "本影片內容僅供教育用途，不構成任何投資建議"

SEGMENT_DURATION = {1: 20, 2: 30, 3: 30, 4: 30, 5: 40, 6: 40, 7: 20}
CHART_SEGMENTS   = {2: 1, 3: 2, 4: 3}

SUBTITLE_HIGHLIGHTS = {
    1: ["股市大漲大跌", "→ 財報"],
    2: ["成績單", "損益表 / 資產負債表\n現金流量表 / 股東權益變動表"],
    3: ["超預期 → ▲", "低於預期 → ▼", "展望悲觀 → ▼"],
    4: ["Q1：4月中－5月底", "Q2：7月中－8月底",
        "Q3：10月中－11月底", "Q4：1月中－2月底"],
    5: ["① EPS 每股盈餘", "② 營收年增率", "③ 展望（Guidance）"],
    6: ["EPS 4.2 > 預期 3.8", "營收年增 31%｜連8季正成長",
        "下季展望 +25%", "（虛構示範數據）"],
    7: ["追蹤頻道", "下一集：快速判讀真實財報"],
}


def compose_video(config: dict) -> dict:
    note = config.get("compose_note", "")
    if note:
        print(f"[合成] 套用修改意見：{note}")

    output_path = OUTPUT_DIR / "financial_report_intro.mp4"
    preview_dir = OUTPUT_DIR / "previews"
    preview_dir.mkdir(exist_ok=True)

    # moviepy import 獨立檢查，給出明確錯誤訊息
    try:
        import moviepy  # noqa: F401
    except ImportError:
        print("  [錯誤] moviepy 未安裝。安裝指令：pip install moviepy")
        return {
            "path": output_path,
            "previews": {},
            "method": "（未生成，需安裝 moviepy）",
        }

    # 合成執行，捕捉所有例外並印出完整原因
    try:
        _compose_with_moviepy(config, output_path, preview_dir)
        previews = _extract_previews(output_path, preview_dir)
        method = "moviepy"
    except Exception as e:
        import traceback
        print(f"\n  [合成錯誤] {type(e).__name__}: {e}")
        print("  完整 traceback：")
        traceback.print_exc()
        return {
            "path": output_path,
            "previews": {"錯誤": str(e)},
            "method": f"合成失敗：{type(e).__name__}",
        }

    return {"path": output_path, "previews": previews, "method": method}


def _resolve_chart_path(chart_id: int, config: dict) -> Path | None:
    """config 優先，若無則 fallback 到 CHARTS_DIR 已存在的檔案。"""
    chart_files = {
        1: CHARTS_DIR / "chart1_four_statements.png",
        2: CHARTS_DIR / "chart2_eps_comparison.png",
        3: CHARTS_DIR / "chart3_earnings_calendar.png",
    }
    # config 傳入的路徑
    from_config = config.get("charts", {}).get(chart_id)
    if from_config and Path(from_config).exists():
        return Path(from_config)
    # fallback：直接從 charts/ 目錄抓
    fallback = chart_files.get(chart_id)
    if fallback and fallback.exists():
        print(f"  [fallback] 圖表{chart_id} 從 CHARTS_DIR 載入：{fallback}")
        return fallback
    return None


def _resolve_audio_path(config: dict) -> Path | None:
    """config 優先，若無則 fallback 到 audio/narration.mp3。"""
    from_config = config.get("audio", {}).get("path")
    if from_config and Path(str(from_config)).exists():
        return Path(from_config)
    fallback = AUDIO_DIR / "narration.mp3"
    if fallback.exists():
        print(f"  [fallback] 音檔從 AUDIO_DIR 載入：{fallback}")
        return fallback
    return None


def _compose_with_moviepy(config, output_path, preview_dir):
    from moviepy import (
        ImageClip, AudioFileClip, CompositeVideoClip,
        TextClip, concatenate_videoclips, ColorClip,
    )

    W, H = 1920, 1080
    clips = []

    for seg_id, duration in SEGMENT_DURATION.items():
        print(f"\n[段落 {seg_id}] duration={duration}s")
        layers = [ColorClip(size=(W, H), color=(26, 26, 46)).with_duration(duration)]

        # 圖表層（左側 60%）
        chart_id   = CHART_SEGMENTS.get(seg_id)
        chart_path = _resolve_chart_path(chart_id, config) if chart_id else None
        if chart_path:
            print(f"  [圖表] ✓ 載入 chart{chart_id}：{chart_path}")
            chart_clip = (ImageClip(str(chart_path))
                          .with_duration(duration)
                          .resized(width=int(W * 0.6))
                          .with_position((0, (H - int(H * 0.9)) // 2)))
            layers.append(chart_clip)
        elif chart_id:
            print(f"  [圖表] ✗ chart{chart_id} 找不到，跳過")

        # 字幕層（右側 40%）
        for i, text in enumerate(SUBTITLE_HIGHLIGHTS.get(seg_id, [])):
            txt = (TextClip(font=_find_cjk_font(), text=text,
                            font_size=36, color="white",
                            size=(int(W * 0.36), None), method="caption")
                   .with_duration(duration)
                   .with_position((int(W * 0.62), 100 + i * 130)))
            layers.append(txt)
        print(f"  [字幕] {len(SUBTITLE_HIGHLIGHTS.get(seg_id, []))} 行")

        clips.append(CompositeVideoClip(layers, size=(W, H)).with_duration(duration))

    video = concatenate_videoclips(clips)
    print(f"\n[合成] 總時長：{video.duration:.1f}s，解析度：{W}x{H}")

    # 音訊層
    audio_path = _resolve_audio_path(config)
    if audio_path:
        print(f"[音訊] ✓ 載入：{audio_path}")
        audio     = AudioFileClip(str(audio_path))
        end_t     = min(video.duration, audio.duration)
        print(f"  影片長度：{video.duration:.1f}s，音檔長度：{audio.duration:.1f}s，裁切至：{end_t:.1f}s")
        audio     = audio.subclipped(0, end_t)
        video     = video.with_audio(audio)
    else:
        print("[音訊] ✗ 找不到音檔，輸出無聲版本")

    print(f"[輸出] 寫入：{output_path}")
    video.write_videofile(str(output_path), fps=30,
                          codec="libx264", audio_codec="aac", logger=None)


def _extract_previews(video_path: Path, preview_dir: Path) -> dict:
    try:
        from moviepy import VideoFileClip
        clip  = VideoFileClip(str(video_path))
        total = clip.duration
        paths = {}
        for label, t in [("第0秒", 0), ("中間", total / 2), ("最後1秒", max(0, total - 1))]:
            img_path = preview_dir / f"preview_{label}.png"
            clip.save_frame(str(img_path), t=t)
            paths[label] = img_path
        clip.close()
        return paths
    except Exception as e:
        return {"錯誤": str(e)}
