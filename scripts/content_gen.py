import google.generativeai as genai
import json
import logging
import os
import time
from dotenv import load_dotenv

load_dotenv("config/.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

log = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2  # seconds; exponential backoff: 2s, 4s between attempts

_DEFAULT_SEARCH_QUERIES = [
    "stock market trading screen",
    "financial chart growth",
    "corporate earnings report",
    "semiconductor chip technology",
    "business finance dashboard",
    "stock exchange trading floor",
    "technology data center",
    "AI processor chip",
    "financial technology screen",
    "global stock market",
]

_PROMPT = """你是一位專業的財經 YouTube Shorts 腳本作家，擅長將財報數字轉化為觀眾聽得懂的故事。

請為以下主題創作一支 60 秒的 YouTube Shorts 腳本：
主題：{topic}

以下是已驗證的財經研究資料，這是你唯一可以使用的數字來源：
---
{research}
---

【資料使用規則，必須嚴格遵守】
- 只能使用上方「已驗證研究資料」中出現的數字，禁止使用你訓練資料或記憶中的舊數字，也禁止自行編造未列出的數字
- 若上方資料中某項目標示「查無資料」、未提及、或整段資料標示無法取得，該項目在旁白中改用質化描述帶過（例如「本季獲利表現穩健」「維持成長動能」），絕對不要為了湊數字而憑空生成
- chart_data 的每一個數值都必須直接對應到上方資料中出現的數字；找不到對應數字的欄位請留空陣列 []，不可捏造

【重要】若上方資料充分，旁白應包含以下具體數字，每一項都要有實際數字，不得用「大幅成長」「顯著提升」等模糊描述帶過：
1. 營收（新台幣或美元，含年增率 %）
2. 毛利率（%）
3. 營業利益（含年增率 %）
4. 淨利（含年增率 %）
5. EPS（每股盈餘）
6. 至少一項前瞻指引或法說會重點（例如下季營收展望）

請只回覆 JSON，格式如下：
{{
  "title": "影片標題（含數字更吸睛，15字內）",
  "narration": "完整旁白（繁體中文，300-400字，60秒長度；依下方圖表標記規則在適當位置插入 [CHART1][CHART2][CHART3]，每個標記各自獨佔一行）",
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

圖表標記規則（必須執行）：
- 依主題類型在旁白中插入標記，每個標記單獨佔一行，前後無其他文字
- 教育型主題（含：如何、入門、風險、概念、教學、什麼是、新手）→ 插入 [CHART1][CHART2][CHART3]
- 財報型主題（含：財報、EPS、營收、毛利率、具體公司財報分析）→ 插入 [CHART1][CHART2]
- 市場型主題（含：週報、大盤、本週行情、三大指數、週一台股）→ 插入 [CHART1]
- 放置時機：緊接在「首次出現具體數字或數據對比」的句子之前
- 相鄰兩個標記之間必須間隔至少 50 個字（約 10 秒配音）
- 標記在配音階段自動移除，不影響旁白語音，觀眾不會聽到
- 格式範例（標記單獨一行）：

  「...這波上漲背後有一個關鍵數字。
  [CHART1]
  台積電近一季毛利率達到53.1%，創下近八季新高...」

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
- 只能使用上方「已驗證研究資料」中出現的數字，不可捏造，也不可使用訓練資料中的舊數字
- 找不到對應數字的欄位留空陣列 []
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


_NO_RESEARCH_DATA = "（未提供已驗證研究資料，禁止捏造具體數字，本題材請改用質化描述）"


def _extract_json(text: str) -> str:
    """Strip ```json / ``` code fences if the model added them despite JSON mode."""
    text = text.strip()
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text


def _validate_and_fill(result: dict, topic: str) -> dict:
    """Ensure required fields (title, narration, search_queries) exist with sane
    types. Missing or malformed fields get a safe default instead of letting
    a KeyError/TypeError crash the pipeline downstream."""
    if not isinstance(result, dict):
        log.warning("Gemini 回傳非 JSON 物件，改用空白腳本套用預設值")
        result = {}

    title = result.get("title")
    if not isinstance(title, str) or not title.strip():
        log.warning("腳本缺少有效 title，改用主題作為預設標題")
        result["title"] = (topic.strip()[:15] if topic and topic.strip() else "財經快訊")

    narration = result.get("narration")
    if not isinstance(narration, str) or not narration.strip():
        log.warning("腳本缺少有效 narration，改用預設旁白")
        result["narration"] = (
            f"{topic or '本集主題'}。腳本生成異常，暫無法提供完整分析內容，請關注後續更新。"
            "本影片僅供教育用途，不構成投資建議。"
        )

    search_queries = result.get("search_queries")
    if not isinstance(search_queries, list) or not all(
        isinstance(q, str) and q.strip() for q in search_queries
    ):
        log.warning("腳本缺少有效 search_queries，改用預設關鍵字組")
        result["search_queries"] = list(_DEFAULT_SEARCH_QUERIES)

    return result


def generate_script(
    topic: str,
    narration_override: str | None = None,
    research_data: str | None = None,
) -> dict:
    """Generate the video script via Gemini.

    research_data: pre-fetched, verified financial facts (e.g. gathered by
    Firecrawl before calling this function) that Gemini must treat as its only
    source of numbers — Gemini's role here is copywriting/formatting, not
    fact-finding. When omitted, the prompt instructs Gemini to fall back to
    qualitative descriptions instead of inventing figures from memory.
    """
    model = genai.GenerativeModel("gemini-2.5-flash")

    if narration_override:
        prompt = _METADATA_PROMPT.format(narration=narration_override.strip())
    else:
        research_text = research_data.strip() if research_data and research_data.strip() else ""
        if not research_text:
            log.warning("未提供 research_data，改用質化描述模式（不捏造數字）")
            research_text = _NO_RESEARCH_DATA
        prompt = _PROMPT.format(topic=topic, research=research_text)

    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")

    result: dict | None = None
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            result = json.loads(_extract_json(response.text))
            break
        except Exception as e:
            last_exc = e
            if attempt < _MAX_RETRIES:
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                log.warning(
                    f"Gemini 腳本生成失敗（第 {attempt}/{_MAX_RETRIES} 次）：{e}，"
                    f"{delay}s 後重試"
                )
                time.sleep(delay)
            else:
                log.error(f"Gemini 腳本生成連續失敗 {_MAX_RETRIES} 次：{e}")

    if result is None:
        result = {}

    result = _validate_and_fill(result, topic)

    if narration_override:
        result["narration"] = narration_override.strip()

    return result
