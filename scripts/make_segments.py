#!/usr/bin/env python3
"""make_segments.py — CLI preview of the dynamic slot timeline for an existing output.

Usage:
    python scripts/make_segments.py [output_dir]

If output_dir is omitted the latest directory under /mnt/d/yt-shorts-finance/output/
is chosen automatically.  The script reads script.json, narration.srt, and
narration_charts.json (if present), then prints the slot table — no media is generated.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.slot_allocator import build_slot_plan, print_slot_table

_OUTPUT_ROOT = Path("/mnt/d/yt-shorts-finance/output")


def _latest_output_dir() -> Path:
    dirs = [d for d in _OUTPUT_ROOT.iterdir() if d.is_dir() and d.name.isdigit()]
    if not dirs:
        raise FileNotFoundError(f"output 目錄下沒有任何執行記錄：{_OUTPUT_ROOT}")
    return max(dirs, key=lambda d: int(d.name))


def _detect_content_type(script: dict, topic: str) -> str:
    topic_l      = topic.lower()
    narration_l  = (
        (script.get("narration") or "") + " " + (script.get("title") or "")
    ).lower()

    topic_edu = ["如何", "教學", "什麼是", "怎麼看", "入門", "新手", "基礎", "怎麼", "how to"]
    if any(k in topic_l for k in topic_edu):
        return "education"

    narration_edu = ["教學", "什麼是", "怎麼看", "入門指南", "新手必看"]
    if any(k in narration_l for k in narration_edu):
        return "education"

    market_kws = [
        "道瓊", "標普", "納斯達克", "大盤", "費半", "週報", "周報",
        "三大指數", "加權指數", "taiex", "computex",
        "美股爆", "週五美股", "週一台股", "概念股", "週五", "美股週",
        "三件事", "多家公司",
    ]
    if any(k in (topic_l + " " + narration_l) for k in market_kws):
        return "market"

    chart_data = script.get("chart_data") or {}
    if chart_data.get("revenue") or chart_data.get("eps"):
        return "earnings"

    return "market"


def main() -> None:
    if len(sys.argv) >= 2:
        out_dir = Path(sys.argv[1])
    else:
        out_dir = _latest_output_dir()
        print(f"自動選取最新目錄：{out_dir}")

    if not out_dir.is_dir():
        print(f"錯誤：目錄不存在：{out_dir}", file=sys.stderr)
        sys.exit(1)

    script_path = out_dir / "script.json"
    srt_path    = str(out_dir / "narration.srt")
    charts_path = str(out_dir / "narration_charts.json")

    if not script_path.exists():
        print(f"錯誤：找不到 script.json：{script_path}", file=sys.stderr)
        sys.exit(1)
    if not Path(srt_path).exists():
        print(f"錯誤：找不到 narration.srt：{srt_path}", file=sys.stderr)
        sys.exit(1)

    script         = json.loads(script_path.read_text(encoding="utf-8"))
    topic          = script.get("title", "")
    search_queries = script.get("search_queries") or script.get("visual_prompts", [])
    content_type   = _detect_content_type(script, topic)

    slot_plan      = build_slot_plan(srt_path, charts_path, search_queries, content_type)
    total_duration = slot_plan[-1].end if slot_plan else 0.0

    print(f"題材類型：{content_type}")
    print_slot_table(slot_plan, total_duration, topic)

    charts_p = Path(charts_path)
    if charts_p.exists():
        data = json.loads(charts_p.read_text(encoding="utf-8"))
        print(f"\n[CHARTn] 時間戳（narration_charts.json）：{data}")
    else:
        print("\n（narration_charts.json 不存在，使用比例 fallback）")


if __name__ == "__main__":
    main()
