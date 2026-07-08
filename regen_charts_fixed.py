#!/usr/bin/env python3
"""Regenerate only the 3 chart clips with fixed CJK font.

Reads risk_edu_charts from script.json and overwrites:
  clip_07.mp4  — CHART1 diverging_bar (歷史重大熊市跌幅)
  clip_12.mp4  — CHART2 diverging_bar (台股近期多空拉鋸)
  clip_17.mp4  — CHART3 horizontal_bar (投資前先確認資金規劃)
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from stage3_risk_edu_assets import _make_diverging, _make_horizontal, _CHART_MAKERS

OUT_DIR  = Path("/mnt/d/yt-shorts-finance/output/risk_education_segments")
SCRIPT_P = OUT_DIR / "script.json"

CHART_JOBS = [
    ("CHART1", "clip_07.mp4"),
    ("CHART2", "clip_12.mp4"),
    ("CHART3", "clip_17.mp4"),
]

def main():
    script      = json.loads(SCRIPT_P.read_text(encoding="utf-8"))
    risk_charts = script.get("risk_edu_charts", {})

    for marker, clip_name in CHART_JOBS:
        spec       = risk_charts.get(marker, {})
        chart_type = spec.get("type", "diverging_bar")
        out_path   = str(OUT_DIR / clip_name)
        maker      = _CHART_MAKERS.get(chart_type)
        if maker is None:
            print(f"  [{marker}] 未知圖表類型 '{chart_type}'，跳過")
            continue

        print(f"  [{marker}] {chart_type} → {clip_name} ...", flush=True)
        t0 = time.time()
        maker(spec, out_path, duration=8)
        elapsed = time.time() - t0
        print(f"         完成（{elapsed:.1f}s）")

    print("\n三張圖表重新生成完畢。中文應正常顯示。")

if __name__ == "__main__":
    main()
