#!/usr/bin/env python3
"""Stage 2 — TTS 配音 + Slot 時間對照表（risk_education_segments）。

執行後：
  - 生成 narration.mp3 + narration.srt + narration_charts.json
  - 印出 Slot 時間對照表供確認
  - 不下載任何素材
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scripts.tts import synthesize
from scripts.slot_allocator import build_slot_plan, print_slot_table

OUT_DIR   = Path("/mnt/d/yt-shorts-finance/output/risk_education_segments")
SCRIPT    = OUT_DIR / "script.json"

def main():
    if not SCRIPT.exists():
        print(f"ERROR: 找不到 {SCRIPT}，請先執行 gen_risk_edu_script.py", file=sys.stderr)
        sys.exit(1)

    script         = json.loads(SCRIPT.read_text(encoding="utf-8"))
    narration      = script["narration"]
    search_queries = script.get("search_queries", [])

    audio_path  = str(OUT_DIR / "narration.mp3")
    srt_path    = str(OUT_DIR / "narration.srt")
    charts_path = str(OUT_DIR / "narration_charts.json")

    char_count = len(narration.replace(" ", "").replace("\n", ""))
    print(f"旁白字數：{char_count} 字")
    print("正在合成語音（Edge TTS）...", flush=True)

    duration = synthesize(narration, audio_path, srt_path=srt_path, charts_path=charts_path)
    print(f"語音時長：{duration:.1f} 秒（{duration/60:.1f} 分鐘）")

    # 印出 narration_charts.json 內容
    charts_p = Path(charts_path)
    if charts_p.exists():
        timestamps = json.loads(charts_p.read_text(encoding="utf-8"))
        print(f"\n[CHARTn] 時間戳：{timestamps}")
    else:
        print("\n（未偵測到 [CHARTn] 標記，將使用比例 fallback）")

    # ── Slot 對照表（education 型，因為 topic 含「教學」相關）────────────────
    content_type = "education"
    slot_plan    = build_slot_plan(srt_path, charts_path, search_queries, content_type)
    total_dur    = slot_plan[-1].end if slot_plan else duration

    print_slot_table(slot_plan, total_dur, script.get("title", ""))

    # 摘要統計
    n_chart = sum(1 for s in slot_plan if s.type == "chart")
    n_video = len(slot_plan) - n_chart
    print(f"\n  預計下載影片片段：{n_video} 個")
    print(f"  預計生成圖表片段：{n_chart} 個")
    print(f"  合計 Slot：{len(slot_plan)} 個")
    print(f"\n確認後，執行 stage3_risk_edu_assets.py 開始下載素材。")

if __name__ == "__main__":
    main()
