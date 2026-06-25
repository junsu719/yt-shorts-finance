# Firecrawl 財報數據整合設計

**日期：** 2026-06-25
**狀態：** 已確認，待實作

---

## 背景與目標

YT Shorts Finance Pipeline 的 Stage 1（`content_gen.py`）目前由 Gemini 2.5 Flash 憑訓練資料產生財報數字。整合 Firecrawl 後，pipeline 可在生成腳本前先抓取真實 IR 頁面內容，並將數據注入 prompt，讓 Gemini 優先使用真實公開財報數字填寫 `chart_data`。

---

## 架構概覽

```
main.py  Stage 1
  ├── should_fetch(topic) → bool          # 關鍵字過濾，決定是否觸發 Firecrawl
  ├── fetch_financials(topic) → str       # 兩段式抓取
  │     ├── search(query, limit=3)        # Firecrawl search 找 IR 頁面 URL
  │     └── scrape_url(url)              # Firecrawl scrape 取 markdown 內容
  └── generate_script(topic,
        narration_override,
        financial_data)                  # 注入財報數據至 prompt 尾端
```

---

## 元件設計

### 1. `scripts/fetch_financials.py`（新增）

**`should_fetch(topic: str) -> bool`**

- 觸發關鍵字（不區分大小寫）：`財報、Q1、Q2、Q3、Q4、EPS、法說、earnings、quarterly、results`
- 不含任何關鍵字 → 直接回傳 `False`，不消耗 Firecrawl credits

**`fetch_financials(topic: str) -> str`**

兩段式流程：
1. **Search**：呼叫 `FirecrawlApp.search(f"{topic} investor relations quarterly results 2025", limit=3)`，取第一筆結果的 URL
2. **Scrape**：呼叫 `FirecrawlApp.scrape_url(url, params={'formats': ['markdown']})`，取 markdown 內容

錯誤處理：
- 任何例外（網路逾時、無結果、解析失敗）均 `except Exception` catch
- Log `WARNING` 說明原因
- 回傳空字串 `""`（graceful degrade）

回傳值截取前 **3000 字**，避免超出 Gemini context window。

### 2. `scripts/content_gen.py`（修改）

`generate_script()` 簽名變更：

```python
# 修改前
def generate_script(topic: str, narration_override: str | None = None) -> dict:

# 修改後
def generate_script(topic: str, narration_override: str | None = None, financial_data: str = "") -> dict:
```

注入邏輯（只附加在 prompt 尾端，不改原有結構）：

```python
if financial_data:
    prompt += (
        "\n\n【參考財報數據 — 以下為 IR 頁面爬取內容，"
        "請優先用這些數字填寫 chart_data；若數字不符請忽略】\n"
        + financial_data[:3000]
    )
```

`narration_override` 路徑（`_METADATA_PROMPT`）也同樣套用，不跳過。

### 3. `main.py`（修改）

Stage 1 `generate_script()` 呼叫前插入：

```python
from scripts.fetch_financials import should_fetch, fetch_financials

# 在 generate_script 呼叫前
financial_data = ""
if should_fetch(topic):
    log.info("  [財報數據] 觸發 Firecrawl 抓取...")
    financial_data = fetch_financials(topic)
    if financial_data:
        log.info(f"  [財報數據] 取得 {len(financial_data)} 字元")
    else:
        log.info("  [財報數據] 抓取失敗，略過（pipeline 繼續）")

script = generate_script(topic, narration_override=narration_override, financial_data=financial_data)
```

### 4. `config/.env`（修改）

新增一行（值留空，由使用者填入）：

```
# Firecrawl API
FIRECRAWL_API_KEY=
```

`fetch_financials.py` 以 `os.getenv("FIRECRAWL_API_KEY")` 讀取。

---

## 安裝

```bash
source ~/yt-shorts-finance/venv/bin/activate
pip install firecrawl-py
```

---

## 搜尋策略決策記錄

| 方案 | 說明 | 結論 |
|---|---|---|
| A. 單一英文搜尋 | `"{topic} investor relations quarterly results 2025"` | ✅ 採用 |
| B. 中英雙搜尋 | 先英文搜，沒找到再補中文 | 捨棄（credits 加倍，邏輯複雜） |
| C. site: domain 搜尋 | 需維護公司→domain 對照表 | 捨棄（不通用） |

觸發方式：
- 永遠執行 → 捨棄（浪費 credits）
- **topic 關鍵字過濾** → ✅ 採用
- CLI flag 手動控制 → 捨棄（增加使用摩擦）

---

## 不在此次範圍內

- Firecrawl search 命中第 2、3 筆結果的 fallback 邏輯
- 抓取結果的快取（同一公司多次執行重複抓取）
- 自動驗證抓到的財報數字與 Gemini 輸出一致性
