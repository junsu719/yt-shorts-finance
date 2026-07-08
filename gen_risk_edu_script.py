#!/usr/bin/env python3
"""Stage 1 — 生成「台股漲了50%」風險教育腳本。

執行後：
  - 印出完整旁白供確認
  - 儲存 output/risk_education_segments/script.json（含 risk_edu_charts 自訂圖表規格）
"""
import json
import os
import sys
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("config/.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

OUT_DIR = Path("/mnt/d/yt-shorts-finance/output/risk_education_segments")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 圖表規格（不交給 Gemini，直接寫死）────────────────────────────────────────
RISK_EDU_CHARTS = {
    "CHART1": {
        "type": "diverging_bar",
        "data": [-78, -60, -50],
        "labels": ["2000科技泡沫\n納斯達克", "2008金融海嘯\n台股", "2022科技崩跌\n成長股"],
        "title": "歷史重大熊市跌幅",
        "unit": "%",
    },
    "CHART2": {
        "type": "diverging_bar",
        "data": [-640, -1057, 211],
        "labels": ["週二 6/23", "週三 6/24", "週四 6/25"],
        "title": "台股近期多空拉鋸",
        "unit": "點",
    },
    "CHART3": {
        "type": "horizontal_bar",
        "data": [100, 70, 30],
        "labels": ["月收入100%", "生活必要支出70%", "可投資金額30%"],
        "title": "投資前先確認資金規劃",
        "highlight_index": 2,
    },
}

PROMPT = """你是一位台灣財經 YouTube 教學頻道的腳本作家。

請為以下主題創作一支 3-4 分鐘長片的完整旁白腳本。

主題：「台股漲了50%，但你真的準備好了嗎？」
目標觀眾：剛進場的新手投資人
語氣：像朋友提醒，溫和但直接，不是恐嚇

旁白長度：700-800字（繁體中文）

六段結構（請嚴格依照，不得標示段落標題）：

第1段【開場Hook，約80字】
- 用讓人心頭一緊的具體情境切入（例如「上週朋友說他賺了50萬⋯⋯」這類場景）
- 點出「帳面獲利」和「真正準備好了嗎」的落差

第2段【多頭市場的幻覺，約160字】
- 解釋「在漲的市場賺錢」和「真的會投資」是兩回事
- 多頭市場讓所有人看起來都是天才
- 這段不要有數字圖表，純文字說理

第3段【歷史告訴我們什麼？，約160字】
- 首句之前先插入圖表標記：[CHART1]（單獨一行，前後換行）
- 提到三個歷史案例：2000年科技泡沫（納斯達克跌78%）、2008年金融海嘯（台股跌60%）、2022年科技崩跌（成長股跌50%）
- 強調這些跌幅比大多數人記憶中更慘
- 不要說教，用敘述的方式讓數字說話

第4段【盤整期代表什麼？，約160字】
- 首句之前先插入圖表標記：[CHART2]（單獨一行，前後換行）
- 提到台股近期多空拉鋸：週二跌640點、週三跌1057點、週四漲211點
- 說明這種震盪本身不是壞事，盤整是上漲後的正常現象
- 短期波動不代表趨勢反轉

第5段【風險管理三個觀念，約200字】
- 「資金規劃」部分之前先插入圖表標記：[CHART3]（單獨一行，前後換行）
- 三個具體建議：
  ① 只用你承受得起全部損失的錢來投資
  ② 分批進場，降低買在高點的時間風險
  ③ 設定停損線、定期檢視，不要因情緒加碼
- 強調「這不是要你出場，而是讓你待得更久」

第6段【結尾CTA，約80字】
- 溫和總結：市場上漲是好事，做好風險管理才能持盈保泰
- Call to action：追蹤頻道、下集聊個股選擇

格式規則（不得違反）：
- [CHART1]、[CHART2]、[CHART3] 各自獨佔一行，前後各空一行
- 整篇是連貫的旁白，不要標示「第N段」「段落一」等任何章節標題
- 禁止開頭用「嘿」「你知道嗎」「讓我們來看看」「話不多說」等口頭禪
- 結尾禁止放投資警語（另外處理）
- 數字以中文形式表達（例如「跌了78%」不要寫「跌了七十八%」）

只輸出旁白文字，不要加任何說明或格式標記。"""

METADATA_PROMPT = """根據以下旁白，生成影片標題、搜尋關鍵字與標籤。
只回覆 JSON，不要其他說明。

旁白：
{narration}

格式：
{{
  "title": "影片標題（15字內，有數字更好）",
  "search_queries": [
    "stock market correction",
    "financial risk management",
    "taiwan stock market",
    "bear market historical data",
    "investment portfolio diversification",
    "stock market volatility",
    "financial planning chart",
    "market bubble burst",
    "trading screen data",
    "business finance analysis"
  ],
  "hashtags": ["#台股", "#投資", "#風險管理", "#新手投資", "#財經教學"]
}}

search_queries 規則：恰好10個，英文3-5單字，須與股市/財務/風險主題相關，絕對不要食品/運動/生活消費類詞彙。"""


def main():
    model = genai.GenerativeModel("gemini-2.5-flash")

    print("Step 1/2 — 生成旁白...", flush=True)
    narration_resp = model.generate_content(PROMPT)
    narration = narration_resp.text.strip()

    print("Step 2/2 — 生成標題 / 關鍵字...", flush=True)
    meta_resp = model.generate_content(METADATA_PROMPT.format(narration=narration))
    meta_text = meta_resp.text.strip()
    if "```json" in meta_text:
        meta_text = meta_text.split("```json")[1].split("```")[0].strip()
    elif "```" in meta_text:
        meta_text = meta_text.split("```")[1].split("```")[0].strip()
    meta = json.loads(meta_text)

    script = {
        "title":            meta.get("title", "台股漲50%，你準備好了嗎？"),
        "narration":        narration,
        "search_queries":   meta.get("search_queries", []),
        "hashtags":         meta.get("hashtags", []),
        "risk_edu_charts":  RISK_EDU_CHARTS,
    }

    out_path = OUT_DIR / "script.json"
    out_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 印出結果 ──────────────────────────────────────────────────────────────
    char_count = len(narration.replace(" ", "").replace("\n", ""))
    marker_count = sum(narration.count(f"[CHART{i}]") for i in range(1, 4))

    print()
    print("=" * 70)
    print(f"  標題：{script['title']}")
    print(f"  字數：{char_count} 字（目標 700-800）")
    print(f"  圖表標記：{marker_count} 個（目標 3）")
    print(f"  儲存至：{out_path}")
    print("=" * 70)
    print()
    print(narration)
    print()
    print("=" * 70)
    print("旁白確認後，執行下一步（TTS + Slot 對照表）。")


if __name__ == "__main__":
    main()
