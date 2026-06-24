import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv("config/.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

_PROMPT = """你是一位專業的財經 YouTube Shorts 腳本作家，擅長將財報數字轉化為觀眾聽得懂的故事。

請根據最新公開財報資料，為以下主題創作一支 60 秒的 YouTube Shorts 腳本：
主題：{topic}

【重要】旁白必須包含以下所有具體數字，每一項都要有實際數字，不得用「大幅成長」「顯著提升」等模糊描述帶過：
1. 營收（新台幣或美元，含年增率 %）
2. 毛利率（%）
3. 營業利益（含年增率 %）
4. 淨利（含年增率 %）
5. EPS（每股盈餘）
6. 至少一項前瞻指引或法說會重點（例如下季營收展望）

請只回覆 JSON，格式如下：
{{
  "title": "影片標題（含數字更吸睛，15字內）",
  "narration": "完整旁白（繁體中文，300-400字，60秒長度）",
  "visual_prompts": [
    "scene 1: English prompt, financial setting, 9:16 vertical, cinematic, no text, no faces",
    "scene 2: ...",
    "scene 3: ..."
  ],
  "search_queries": [
    "stock market candlestick chart",
    "financial bar chart growth",
    "smartphone camera lens optics",
    "technology stock trading screen",
    "corporate earnings financial data",
    "semiconductor wafer fabrication",
    "server data center cooling",
    "stock exchange trading floor",
    "AI chip processor technology",
    "business finance dashboard"
  ],
  "chart_data": {{
    "company": "公司名稱",
    "currency": "NTD 或 USD",
    "unit": "億 或 百萬",
    "quarters": ["2023Q2", "2023Q3", "2023Q4", "2024Q1"],
    "revenue": [480, 546, 625, 592],
    "gross_margin": [54.1, 53.2, 53.0, 53.1],
    "net_profit": [200, 211, 262, 225],
    "eps": [7.7, 8.14, 10.13, 8.7],
    "yoy_growth": [3.2, 13.7, 15.0, 16.5],
    "segments": {{"HPC": 52, "Smartphone": 33, "IoT": 7, "Auto": 5, "Others": 3}}
  }},
  "hashtags": ["#財經", "#投資", "#Shorts"]
}}

旁白風格：
- 語氣像財經主播在播報，自然流暢，不要煽情也不要口語化問句
- 禁止使用「嘿」「你知道嗎」「讓我們來看看」「話不多說」等口頭禪
- 開頭直接破題，第一句就是最重要的數字事實
- 禁止使用「老黃」稱呼 NVIDIA 執行長；統一使用英文名：第一次提及用「Jensen Huang」，後續可簡稱「Jensen」

旁白結構：
- 【Hook 5秒】第一句直接是核心數字（例如「台積電單季淨利2254億，年增8.9%。」）
- 【營收與毛利 15秒】說清楚這季賺多少、毛利率幾%、跟去年比差多少
- 【獲利細節 15秒】營業利益、淨利、EPS 逐一點出
- 【亮點或風險 15秒】法說會展望、AI需求/地緣政治/匯率等關鍵因素
- 【結尾 10秒】簡短總結 + call to action（「追蹤我們，掌握更多財報分析。」）

visual_prompts 規則：
- 3-4 個場景，英文
- 具體元素：rising bar charts, semiconductor wafer fab, stock trading screens, financial report data
- 風格：cinematic, dark professional tone, no text overlay, no human faces

search_queries 規則（重要）：
- 恰好 10 個，英文，每個 3-5 個單字
- 用於 Pexels / Pixabay / Mixkit / Vecteezy 搜尋股票影片素材，必須是能搜到的真實關鍵字
- 必須與財報、股市、科技產業相關，例如：stock market, financial chart, semiconductor, camera lens, trading screen
- 嚴禁出現消費品、食物、化妝品、人臉等無關詞彙
- 10 個關鍵字應盡量多樣化，涵蓋不同角度

chart_data 規則（重要）：
- 使用實際公開財報數字，不可捏造
- quarters 最近 4 季，格式 "YYYYQN"
- revenue / net_profit 單位與 unit 欄位一致
- gross_margin 單位為 %（例如 53.5 代表 53.5%）
- eps 為當季每股盈餘（原幣別）
- yoy_growth 為營收年增率（%，可為負數）
- segments 為最新一季業務收入占比（%，合計約 100）
"""


_METADATA_PROMPT = """根據以下旁白，只產生標題、視覺提詞、搜尋關鍵字、財務圖表數據與標籤，請只回覆 JSON：

旁白內容：
{narration}

格式：
{{
  "title": "影片標題（含數字更吸睛，15字內）",
  "visual_prompts": [
    "scene 1: English prompt, match the narration topic, 9:16 vertical, cinematic, no text, no faces",
    "scene 2: ...",
    "scene 3: ..."
  ],
  "search_queries": [
    "stock market trading",
    "semiconductor chip",
    "data center server",
    "stock chart rising",
    "financial technology",
    "AI processor chip",
    "corporate earnings data",
    "trading floor exchange",
    "business finance chart",
    "technology stock market"
  ],
  "chart_data": {{
    "company": "公司名稱",
    "currency": "NTD 或 USD",
    "unit": "億 或 百萬",
    "quarters": ["2023Q2", "2023Q3", "2023Q4", "2024Q1"],
    "revenue": [480, 546, 625, 592],
    "gross_margin": [54.1, 53.2, 53.0, 53.1],
    "net_profit": [200, 211, 262, 225],
    "eps": [7.7, 8.14, 10.13, 8.7],
    "yoy_growth": [3.2, 13.7, 15.0, 16.5],
    "segments": {{"HPC": 52, "Smartphone": 33, "IoT": 7, "Auto": 5, "Others": 3}}
  }},
  "hashtags": ["#財經", "#投資", "#Shorts"]
}}

旁白風格（重要）：
- 禁止使用「老黃」稱呼 NVIDIA 執行長；統一使用英文名：第一次提及用「Jensen Huang」，後續可簡稱「Jensen」

visual_prompts 規則：3-4 個場景，英文，風格 cinematic dark professional，具體元素須與旁白主題相符。

search_queries 規則（重要）：
- 恰好 10 個，英文，每個 3-5 個單字
- 用於 Pexels / Pixabay / Mixkit / Vecteezy 搜尋背景影片，須與旁白主題相關（股市、科技、半導體、財經等）
- 嚴禁出現消費品、食物、化妝品、服飾等無關詞彙

chart_data 規則：使用旁白中提到的實際數字填寫，不可捏造。
"""


def generate_script(topic: str, narration_override: str | None = None) -> dict:
    model = genai.GenerativeModel("gemini-2.5-flash")

    if narration_override:
        prompt = _METADATA_PROMPT.format(narration=narration_override.strip())
    else:
        prompt = _PROMPT.format(topic=topic)

    response = model.generate_content(prompt)
    text = response.text.strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    result = json.loads(text)
    if narration_override:
        result["narration"] = narration_override.strip()
    return result
