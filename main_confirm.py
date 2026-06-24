"""
YT Shorts Finance - 分段確認製作流程
用法：python main_confirm.py
"""

import sys
from pathlib import Path

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
CHARTS_DIR = BASE_DIR / "charts"
AUDIO_DIR  = BASE_DIR / "audio"
ASSETS_DIR = BASE_DIR / "assets"

for d in [OUTPUT_DIR, CHARTS_DIR, AUDIO_DIR, ASSETS_DIR]:
    d.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# 確認機制
# ---------------------------------------------------------------------------

def wait_for_confirm(step_name: str, ok_keyword: str) -> str:
    """
    暫停並等待使用者輸入。
    回傳值：'ok' | 'redo' | 'modify:<content>'
    """
    print(f"\n{'='*60}")
    print(f"[{step_name}] 完成")
    print(f"  輸入 「{ok_keyword}」  → 繼續下一步")
    print(f"  輸入 「重做」          → 重新執行本 Step")
    print(f"  輸入 「修改：[內容]」  → 針對本 Step 進行調整")
    print('='*60)

    while True:
        user_input = input(">>> ").strip()
        if user_input == ok_keyword:
            return "ok"
        elif user_input == "重做":
            return "redo"
        elif user_input.startswith("修改：") or user_input.startswith("修改:"):
            content = user_input.split("：", 1)[-1].split(":", 1)[-1]
            return f"modify:{content}"
        else:
            print(f'  請輸入「{ok_keyword}」、「重做」或「修改：...」')


# ---------------------------------------------------------------------------
# Step 1：腳本
# ---------------------------------------------------------------------------

def step1_script(config: dict) -> dict:
    from steps.step1_script import generate_script
    while True:
        script = generate_script(config)
        config["script"] = script
        print("\n[腳本內容]\n")
        print(script["text"])
        print(f"\n字數：{script['char_count']} 字｜預估時長：{script['estimated_seconds']} 秒")

        result = wait_for_confirm("Step 1 腳本", "腳本OK")
        if result == "ok":
            return config
        elif result == "redo":
            continue
        elif result.startswith("modify:"):
            config["script_note"] = result[7:]


# ---------------------------------------------------------------------------
# Step 2：逐張生成圖表
# ---------------------------------------------------------------------------

def step2_charts(config: dict) -> dict:
    from steps.step2_charts import generate_chart

    chart_specs = [
        {"id": 1, "ok_keyword": "圖表一OK", "name": "四大報表關係圖"},
        {"id": 2, "ok_keyword": "圖表二OK", "name": "預期 vs 實際對比圖"},
        {"id": 3, "ok_keyword": "圖表三OK", "name": "財報季時間軸"},
    ]

    config["charts"] = {}
    for spec in chart_specs:
        while True:
            path = generate_chart(spec["id"], config)
            config["charts"][spec["id"]] = path
            print(f"\n[圖表 {spec['id']}｜{spec['name']}]")
            print(f"  檔案路徑：{path}")

            result = wait_for_confirm(f"Step 2 圖表{spec['id']}", spec["ok_keyword"])
            if result == "ok":
                break
            elif result == "redo":
                continue
            elif result.startswith("modify:"):
                config[f"chart{spec['id']}_note"] = result[7:]

    return config


# ---------------------------------------------------------------------------
# Step 3：配音
# ---------------------------------------------------------------------------

def step3_audio(config: dict) -> dict:
    from steps.step3_audio import generate_audio
    while True:
        audio_info = generate_audio(config)
        config["audio"] = audio_info
        print(f"\n[配音檔案]")
        print(f"  檔案路徑：{audio_info['path']}")
        print(f"  預估秒數：{audio_info['estimated_seconds']} 秒")
        print(f"  段落分佈：{audio_info['segments']}")

        result = wait_for_confirm("Step 3 配音", "配音OK")
        if result == "ok":
            return config
        elif result == "redo":
            continue
        elif result.startswith("modify:"):
            config["audio_note"] = result[7:]


# ---------------------------------------------------------------------------
# Step 4：合成影片
# ---------------------------------------------------------------------------

def step4_compose(config: dict) -> dict:
    from steps.step4_compose import compose_video
    while True:
        video_info = compose_video(config)
        config["video"] = video_info
        print(f"\n[影片合成]")
        print(f"  輸出路徑：{video_info['path']}")
        print(f"  預覽截圖：")
        for label, path in video_info["previews"].items():
            print(f"    {label}：{path}")

        result = wait_for_confirm("Step 4 合成影片", "合成OK")
        if result == "ok":
            return config
        elif result == "redo":
            continue
        elif result.startswith("modify:"):
            config["compose_note"] = result[7:]


# ---------------------------------------------------------------------------
# Step 5：上傳 YouTube
# ---------------------------------------------------------------------------

def step5_upload(config: dict) -> dict:
    from steps.step5_upload import upload_youtube
    while True:
        meta = config.get("youtube_meta", {})
        print(f"\n[YouTube 上傳資訊確認]")
        print(f"  標題：{meta.get('title', '（未設定）')}")
        print(f"  描述：{meta.get('description', '（未設定）')[:80]}...")
        print(f"  標籤：{', '.join(meta.get('tags', []))}")

        result = wait_for_confirm("Step 5 上傳 YouTube", "上傳OK")
        if result == "ok":
            url = upload_youtube(config)
            print(f"\n  上傳完成：{url}")
            return config
        elif result == "redo":
            continue
        elif result.startswith("modify:"):
            config["upload_note"] = result[7:]


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(config: dict):
    print("\n" + "="*60)
    print("  YT Shorts Finance｜分段確認製作流程")
    print("="*60)

    config = step1_script(config)
    config = step2_charts(config)
    config = step3_audio(config)
    config = step4_compose(config)
    config = step5_upload(config)

    print("\n[完成] 所有步驟執行完畢。")
    print(f"  最終影片：{config['video']['path']}")


if __name__ == "__main__":
    VIDEO_CONFIG = {
        "title":  "財報是什麼？為什麼投資人都在看？",
        "topic":  "financial_report_basics",
        "type":   "education",
        "lang":   "zh-TW",
        "fps":    30,
        "width":  1920,
        "height": 1080,
        "youtube_meta": {
            "title": "財報是什麼？為什麼投資人都在看？【投資入門#1】",
            "description": (
                "完全新手也能看懂！三分鐘搞懂財報四大組成、財報季時間、"
                "以及投資人最關注的三個關鍵數字（EPS、營收年增率、展望）。\n\n"
                "⚠️ 本影片內容僅供教育用途，不構成任何投資建議。\n\n"
                "📌 下一集：五分鐘快速判讀一份真實財報"
            ),
            "tags": [
                "財報", "投資入門", "EPS", "損益表", "財報季",
                "股票新手", "投資理財", "台灣股市", "財務報表",
            ],
            "category": "Education",
            "privacy":  "public",
        },
    }
    run(VIDEO_CONFIG)
