import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path

from scripts.content_gen import generate_script
from scripts.tts import synthesize
from scripts.video_gen import fetch_clip
from scripts.image_gen import generate_image, image_to_clip
from scripts.chart_gen import (
    generate_finance_chart, chart_to_clip, CHART_TYPES,
    generate_market_chart, generate_education_chart,
    generate_animated_chart, generate_animated_market_chart,
    generate_etf_dividend_chart, generate_highlight_bar_chart,
)
from scripts.assembler import concat_clips, assemble
from scripts.photo_gen import photo_to_clip, CUSTOM_DIR
from scripts.slot_allocator import build_slot_plan, print_slot_table

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Content type detection ────────────────────────────────────────────────────

def detect_content_type(script: dict, topic: str = "") -> str:
    """Classify topic as 'earnings' | 'market' | 'education' for slot planning.

    Priority: topic string → narration (strict keywords only) → chart_data presence.
    Topic is checked with broad keywords; narration uses a smaller, unambiguous set
    to avoid false positives from phrases like '如何影響台股'.
    """
    topic_l = topic.lower()
    narration_l = (
        (script.get("narration") or "") + " " + (script.get("title") or "")
    ).lower()

    # ── Step 1: education detection — topic takes broad list ─────────────────
    topic_edu = ["如何", "教學", "什麼是", "是什麼", "怎麼看", "入門", "新手", "基礎", "怎麼", "搞懂", "how to"]
    if any(k in topic_l for k in topic_edu):
        return "education"

    # Narration: only unambiguous education markers (避免 '如何影響台股' 誤判)
    narration_edu = ["教學", "什麼是", "怎麼看", "入門指南", "新手必看"]
    if any(k in narration_l for k in narration_edu):
        return "education"

    # ── Step 2: market detection ──────────────────────────────────────────────
    market_kws = [
        "道瓊", "標普", "納斯達克", "大盤", "費半", "週報", "周報",
        "三大指數", "加權指數", "taiex", "computex",
        "美股爆", "週五美股", "週一台股", "概念股", "週五", "美股週",
        "三件事", "多家公司",
    ]
    full_text = topic_l + " " + narration_l
    if any(k in full_text for k in market_kws):
        return "market"

    # ── Step 3: earnings — single company with financial data ─────────────────
    chart_data = script.get("chart_data") or {}
    if chart_data.get("revenue") or chart_data.get("eps"):
        return "earnings"

    return "market"



def _parse_custom_photos(spec: str) -> dict[int, Path]:
    """Parse 'slot2:photo.jpg,slot4:photo2.jpg' → {2: Path(...), 4: Path(...)}"""
    if not spec:
        return {}
    result: dict[int, Path] = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            log.warning(f"  [custom-photos] 無效格式 '{item}'（應為 slotN:filename.jpg），略過")
            continue
        slot_str, filename = item.split(":", 1)
        slot_str = slot_str.strip().lower()
        if not slot_str.startswith("slot"):
            log.warning(f"  [custom-photos] 無法識別 slot '{slot_str}'，略過")
            continue
        try:
            slot_num = int(slot_str[4:])
        except ValueError:
            log.warning(f"  [custom-photos] slot 編號非數字 '{slot_str}'，略過")
            continue
        result[slot_num] = CUSTOM_DIR / filename.strip()
    return result


def run(topic: str, custom_photos: dict[int, Path] | None = None) -> str:
    run_id = int(time.time())
    work = Path(f"/mnt/d/yt-shorts-finance/output/{run_id}")
    work.mkdir(parents=True, exist_ok=True)

    log.info(f"=== 開始製作：{topic} ===")

    # 1. Generate script
    log.info("[1/4] 生成腳本...")
    custom_script_path = Path("custom_script.json")
    if custom_script_path.exists():
        log.info("  使用 custom_script.json（跳過 Gemini）")
        script = json.loads(custom_script_path.read_text(encoding="utf-8"))
    else:
        custom_narration_path = Path("custom_narration.txt")
        narration_override = (
            custom_narration_path.read_text(encoding="utf-8")
            if custom_narration_path.exists() else None
        )
        if narration_override:
            log.info("  使用 custom_narration.txt")

        research_data_path = Path("research_data.txt")
        research_data = (
            research_data_path.read_text(encoding="utf-8")
            if research_data_path.exists() else None
        )
        if research_data:
            log.info("  使用 research_data.txt（已驗證財經資料，供 Gemini 撰寫文案用）")
        elif not narration_override:
            log.warning("  找不到 research_data.txt，Gemini 將無數字來源，旁白會改用質化描述")

        script = generate_script(topic, narration_override=narration_override, research_data=research_data)
    (work / "script.json").write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info(f"  標題：{script['title']}")

    # 2. TTS + SRT
    log.info("[2/4] 語音合成...")
    audio_path  = str(work / "narration.mp3")
    srt_path    = str(work / "narration.srt")
    charts_path = str(work / "narration_charts.json")
    duration    = synthesize(script["narration"], audio_path, srt_path=srt_path, charts_path=charts_path)
    _nar_chars = len(script["narration"].replace(" ", "").replace("\n", ""))
    log.info(f"  旁白字數：{_nar_chars} 字 | 預估秒數：約 {_nar_chars // 5}s（實際 {duration:.0f}s）")

    # 3. Build clips — slot layout determined by content type
    log.info("[3/4] 生成圖表 + 下載背景影片...")

    content_type = detect_content_type(script, topic)
    log.info(f"  題材類型：{content_type}")

    chart_data  = script.get("chart_data") or {}
    use_charts  = bool(
        chart_data.get("revenue") or chart_data.get("eps") or
        chart_data.get("segments") or chart_data.get("yoy_growth")
    )

    # Inject nonfarm education data when topic/narration matches
    _nonfarm_kws = ["非農", "nonfarm", "non-farm", "就業報告"]
    _narration_text = script.get("narration", "")
    _is_nonfarm_edu = content_type == "education" and any(
        k in (topic + _narration_text) for k in _nonfarm_kws
    )
    if _is_nonfarm_edu:
        chart_data = {
            "nonfarm": {
                "expected": 8.5,
                "actual": 17.2,
                "revision": 9.3,
                "unit": "萬人",
                "period": "2026年5月",
            }
        }
        use_charts = False
        log.info("  偵測到非農教育題材，注入自訂圖表資料")

    _etf_div_kws = ["配息", "0050", "0056", "除息"]
    _is_etf_edu = content_type == "education" and any(
        k in (topic + _narration_text) for k in _etf_div_kws
    )
    if _is_etf_edu:
        log.info("  偵測到ETF配息教育題材，啟用配息圖表")
    narration      = script.get("narration", "")
    search_queries = script.get("search_queries") or script.get("visual_prompts", [])
    chart_types    = CHART_TYPES.copy()
    random.shuffle(chart_types)

    slot_plan = build_slot_plan(srt_path, charts_path, search_queries, content_type)
    print_slot_table(slot_plan, duration, topic)
    log.info(f"  Slot 數量：{len(slot_plan)}（動態分配）")

    clip_paths:   list[str]      = []
    seen_ids:     set[str]       = set()
    seen_hashes:  set[str]       = set()
    source_stats: dict[str, int] = {"pexels": 0, "pixabay": 0, "mixkit": 0, "vecteezy": 0, "chart": 0, "custom": 0}
    chart_idx = 0

    if custom_photos:
        log.info(f"  自訂照片：{', '.join(f'slot{k}={v.name}' for k, v in sorted(custom_photos.items()))}")

    for spec in slot_plan:
        clip_path = str(work / f"clip_{spec.index:02d}.mp4")
        label     = f"Slot {spec.index}/{len(slot_plan)}"

        # ── Custom photo override ─────────────────────────────────────────
        custom_path = (custom_photos or {}).get(spec.index)
        if custom_path is not None:
            if custom_path.exists():
                try:
                    src_w, src_h = photo_to_clip(str(custom_path), clip_path, duration=5)
                    log.info(f"  {label}: 自訂照片 [{custom_path.name}] 原始 {src_w}×{src_h} → 1080×1920")
                    source_stats["custom"] += 1
                    clip_paths.append(clip_path)
                    continue
                except Exception as e:
                    log.warning(f"  {label}: 自訂照片處理失敗（{e}），改用素材庫備援")
            else:
                log.warning(f"  {label}: 找不到照片 '{custom_path.name}'（{custom_path}），改用素材庫備援")
        # ─────────────────────────────────────────────────────────────────

        if spec.type == "chart":
            # Education charts still use static PNG → chart_to_clip
            chart_png     = str(work / f"chart_{chart_idx+1:02d}.png")
            chart_success = False
            chart_dur     = spec.duration

            if _is_nonfarm_edu:
                _edu_labels = ["非農比較圖", "好消息壞消息流程圖", "台股走勢示意圖"]
                _edu_label  = _edu_labels[chart_idx % len(_edu_labels)]
                try:
                    generate_education_chart(chart_data, chart_idx, chart_png)
                    chart_to_clip(chart_png, clip_path, duration=chart_dur)
                    log.info(f"  {label}: 教育圖表 [{_edu_label}]")
                    chart_success = True
                except Exception as e:
                    log.warning(f"  {label}: 教育圖表失敗，嘗試動畫圖表: {e}")

            # ETF education charts — list of horizontal-bar specs dispatched by chart_idx
            if not chart_success and _is_etf_edu:
                _etf_charts = chart_data.get("etf_charts", [])
                if chart_idx < len(_etf_charts):
                    cfg = _etf_charts[chart_idx]
                    try:
                        generate_highlight_bar_chart(
                            data=cfg["data"], labels=cfg["labels"],
                            title=cfg["title"], unit=cfg.get("unit", ""),
                            highlight_index=cfg.get("highlight_index", 0),
                            output_path=clip_path,
                            watermark=cfg.get("watermark", "示意圖，非投資建議"),
                            duration=chart_dur,
                        )
                        log.info(f"  {label}: ETF教育圖表 [{cfg['title']}]")
                        chart_success = True
                    except Exception as e:
                        log.warning(f"  {label}: ETF教育圖表失敗: {e}")

            # Animated finance chart — outputs MP4 directly to clip_path
            if not chart_success and use_charts:
                chart_type = chart_types[chart_idx % len(chart_types)]
                try:
                    generate_animated_chart(chart_data, chart_type, clip_path, duration=chart_dur)
                    log.info(f"  {label}: 動畫圖表 [{chart_type}]")
                    chart_success = True
                except Exception as e:
                    log.warning(f"  {label}: 動畫圖表失敗，嘗試動畫市場圖: {e}")

            # Animated market chart fallback — chart_idx rotates chart type
            if not chart_success:
                try:
                    generate_animated_market_chart(narration, clip_path, duration=chart_dur, chart_idx=chart_idx, chart_data=chart_data)
                    log.info(f"  {label}: 動畫市場圖表 [type={chart_idx % 3}]")
                    chart_success = True
                except Exception as e:
                    log.warning(f"  {label}: 動畫市場圖表失敗，改用影片素材: {e}")

            if not chart_success:
                q = spec.query or (search_queries[chart_idx % len(search_queries)] if search_queries else "stock market")
                try:
                    fetch_clip(q, clip_path, source="auto", seen_ids=seen_ids, seen_hashes=seen_hashes,
                               clip_duration=spec.duration)
                    log.info(f"  {label}: 影片備援 query='{q}'")
                except Exception as e:
                    log.error(f"  {label}: 圖表與影片備援皆失敗，改用純色底: {e}")

            source_stats["chart"] += 1
            chart_idx += 1

        else:
            try:
                fetch_clip(spec.query, clip_path, source=spec.source,
                           seen_ids=seen_ids, seen_hashes=seen_hashes,
                           clip_duration=spec.duration)
                log.info(f"  {label}: 影片 [{spec.source}] query='{spec.query}'")
                source_stats[spec.source] += 1
            except Exception as e:
                log.warning(f"  {label}: [{spec.source}] 失敗，改用 auto: {e}")
                try:
                    fetch_clip(spec.query, clip_path, source="auto",
                               seen_ids=seen_ids, seen_hashes=seen_hashes,
                               clip_duration=spec.duration)
                    log.info(f"  {label}: 影片 [auto fallback] query='{spec.query}'")
                    source_stats["auto_fallback"] = source_stats.get("auto_fallback", 0) + 1
                except Exception as e2:
                    log.error(f"  {label}: 影片完全失敗: {e2}")

        clip_paths.append(clip_path)

    parts = [f"pexels={source_stats['pexels']}", f"pixabay={source_stats['pixabay']}",
             f"mixkit={source_stats['mixkit']}", f"vecteezy={source_stats['vecteezy']}",
             f"chart={source_stats['chart']}"]
    if source_stats.get("custom"):
        parts.append(f"custom={source_stats['custom']}")
    if source_stats.get("auto_fallback"):
        parts.append(f"auto_fallback={source_stats['auto_fallback']}")
    log.info(f"  素材統計：{' | '.join(parts)}")

    bg_video = str(work / "background.mp4")
    clip_durations = [s.duration for s in slot_plan]
    concat_clips(clip_paths, bg_video, clip_durations)

    # 4. Assemble final video
    log.info("[4/4] 合成最終影片...")
    final = str(work / "final.mp4")
    assemble(bg_video, audio_path, final, srt_path=srt_path)

    log.info("=== 完成 ===")
    log.info(f"  輸出：{final}")
    log.info(f"  標題：{script['title']}")
    log.info(f"  標籤：{' '.join(script.get('hashtags', []))}")
    return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YT Shorts Finance 影片製作")
    parser.add_argument("positional_topic", nargs="?", default=None, metavar="TOPIC",
                        help="影片主題（與 --topic 二擇一）")
    parser.add_argument("--topic", default=None, help="影片主題")
    parser.add_argument(
        "--custom-photos", default="",
        metavar="SPEC",
        help="自訂照片，格式：slot2:photo.jpg,slot4:photo2.jpg",
    )
    args = parser.parse_args()
    topic = args.topic or args.positional_topic or "台積電最新財報分析"
    run(topic, custom_photos=_parse_custom_photos(args.custom_photos))
