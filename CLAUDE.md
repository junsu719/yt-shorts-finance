# stocks500yt — 影片自動化 Pipeline 專案規範

> 部署位置:WSL2 ~/yt-shorts-finance/CLAUDE.md(GitHub: junsu719/yt-shorts-finance)

## 已確認目標
- 解決:幫台灣人看懂財經新聞(教育型,非投顧)
- 頻道:@stocks500yt,台股優先 + S&P 500 財報
- 內容紅線與風格:一律遵循 ~/claude-bible/skills/yt-shorts-style/SKILL.md

## 執行環境
- WSL2 Ubuntu,`cd ~/yt-shorts-finance && source venv/bin/activate` 後才進 claude
- 互動模式:`python main_confirm.py`(逐步確認);全自動:`python main.py`
- Mac mini M4 為 24/7 排程候選機

## 架構地圖
- scripts/content_gen.py:Gemini 腳本生成,[CHART1~3] 標記(JSON mode + retry 已補)
- scripts/tts.py:TTS + 標記剝離 + narration_charts.json
- scripts/slot_allocator.py:SRT 時間戳 slot 分配(10~12 秒輪動)
- scripts/video_gen.py:四庫素材下載(去重 + _BLOCKED_KEYWORDS)
- scripts/assembler.py:FFmpeg 組裝
- scripts/make_segments.py:長片分段出片(16:9,CapCut 組裝)
- steps/step2_charts.py:三種動畫圖表模板(vertical / horizontal / diverging bar)
- assets/custom/:自製素材(如 micron.jpg、memory_frog.jpg)

> ⚠️ **待查證(2026-07-04 部署聖經時發現)**:本節與下方「YT Shorts Finance 技術規格書」的 Stage 說明並不完全對得上,且 repo 內還有 `main_confirm.py`(完整依賴 `steps/step1_script.py`~`step5_upload.py`)、根目錄 `make_segments.py`(16:9 長片工具)、`stage2~4_risk_edu_*.py`、`diagnose_clips.py` 等模組,目前**完全沒有任何文件描述**。已確認 `main.py` 第21行有 `from scripts.slot_allocator import build_slot_plan, print_slot_table`,證實 slot_allocator 確實整合進主產線,但下方技術規格書的 Stage 3 說明漏了它。這代表現有文件只完整涵蓋 `main.py` 這條 Shorts 產線,`main_confirm.py`/長片工具/risk_edu 系列仍待補寫或確認是否為現役。列為待辦,見專案 `DECISIONS.md`。

## 技術鐵則
- 中文字型:FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
- moviepy 版本鎖定(1.x/2.x 語法不相容)
- 字幕 FontSize 80 + 自動換行,防溢出
- 真實財務數據 = Firecrawl 抓取;Gemini 不得生成數字(詳細機制見下方技術規格書「Stage 0 — 資料查證」)
- fallback 抓取必須傳遞 clip_duration,不得寫死 5 秒;圖表時長不做整數捨入
- 新離題素材出現 → 即時追加 _BLOCKED_KEYWORDS 並回報

## 資源
- Kling AI:660 credits/月,留給高價值動態片段
- 素材四庫:Pixabay + Pexels + Mixkit + Vecteezy(前兩者關鍵字組必須都給)
- 週節奏參考(非硬性配額):週一盤前展望 / 週三教育 / 週五週回顧

---

# YT Shorts Finance — 繁體中文財經短影音自動化系統(技術規格書)

自動產生台股 / S&P 500 財報分析、市場行情、AI 產業動態的 YouTube Shorts 影片。
輸入主題字串，輸出可上傳的直式短影音（1080×1920、含燒錄字幕、繁中配音）。

---

## 影片製作規範（強制執行，每支影片皆適用）

### 規則一：內容定位 — 台股為主、美股為輔

所有市場週報類影片，內容架構必須依照以下順序：

1. **台股本週表現**（主角）— 具體點位、漲跌原因、個股亮點
2. **美股關鍵數據對台股的影響**（配角）— 不是美股總結，而是「台股投資人需要知道的美股資訊」
3. **週末重大事件對週一開盤的影響** — 地緣政治、央行決策等
4. **週一台股盤前三大觀察重點** — 具體、可操作

**禁止**以「美股總結順便提台股」的角度撰寫旁白。

### 規則二：警語位置

- **開場前 3 秒禁止放警語**（Hook 黃金時間，禁止浪費）
- 警語統一移至**影片最後 5 秒**
- 格式固定為：「本影片僅供教育用途，不構成投資建議」
- 旁白結構：`[Hook] → [內容本體] → [CTA] → [警語]`

### 規則三：旁白命名

- 禁止使用「老黃」稱呼 NVIDIA 執行長
- 統一使用「Jensen Huang」（第一次提及）、「Jensen」（後續）

---

## 資料夾結構

```
yt-shorts-finance/
├── main.py                   # 主程式；argparse CLI + 4 段 pipeline
├── custom_narration.txt      # （選用）手動覆蓋 AI 旁白，用後需刪除
├── research_data.txt         # （選用）Firecrawl 抓取的已驗證財經資料，供 Gemini 撰寫文案用，用後需刪除
│
├── scripts/
│   ├── content_gen.py        # Stage 1：Gemini 2.5 Flash 生成腳本 JSON
│   ├── tts.py                # Stage 2：Edge TTS 逐句配音 + ffprobe 精準 SRT
│   ├── video_gen.py          # Stage 3a：Pexels / Pixabay / Mixkit / Vecteezy 下載影片
│   ├── chart_gen.py          # Stage 3b：matplotlib 財經圖表 → 5秒 MP4
│   ├── photo_gen.py          # Stage 3c：自訂照片 9:16 裁切 + Ken Burns → 5秒 MP4
│   ├── image_gen.py          # Stage 3d：Imagen 3 生成 AI 圖像（備用）
│   └── assembler.py          # Stage 4：FFmpeg 合成最終影片
│
├── config/
│   ├── .env                  # API 金鑰（不提交 git）
│   └── client_secret.json    # YouTube OAuth 憑證
│
├── assets/
│   ├── custom/               # ★ 自訂照片放這裡（--custom-photos 使用）
│   ├── audio/
│   │   ├── kokoro-v1.0.int8.onnx   # Kokoro TTS 模型（待整合）
│   │   └── voices-v1.0.bin
│   ├── images/               # 圖片素材暫存
│   ├── subtitles/            # SRT 字幕暫存
│   └── video/                # 下載的背景素材
│
├── output/
│   └── <unix_timestamp>/     # 每次執行產生獨立資料夾
│       ├── script.json
│       ├── narration.mp3
│       ├── narration.srt
│       ├── chart_01~03.png   # matplotlib 圖表
│       ├── clip_01~07.mp4    # 7 段背景素材
│       ├── background.mp4
│       └── final.mp4         # ★ 最終輸出
│
├── logs/
│   └── pipeline.log
└── venv/                     # Python venv（source venv/bin/activate）
```

---

## 工具與 API 清單

| 工具 / API | 用途 | 狀態 | 設定位置 |
|---|---|---|---|
| **Gemini 2.5 Flash** | 腳本生成（旁白、標題、搜尋詞、Hashtag） | 已整合 | `GEMINI_API_KEY` in `.env` |
| **Gemini Imagen 3** | AI 圖像生成（9:16，Ken Burns 轉 4秒 MP4） | 已整合 | 同上 |
| **Edge TTS** (`zh-TW-HsiaoChenNeural`) | 繁體中文 TTS 配音，語速 +5% | 已整合 | 無需 API 金鑰 |
| **Kokoro TTS** | 離線 TTS 引擎（模型已下載至 `assets/audio/`） | 待整合 | — |
| **Pexels API** | 背景影片素材 | 已整合 | `PEXELS_API_KEY` in `.env` |
| **Pixabay API** | 背景影片素材 | 已整合 | `PIXABAY_API_KEY` in `.env` |
| **Mixkit** | 背景影片素材（CDN 爬蟲，無需 API 金鑰） | 已整合 | — |
| **Vecteezy API** | 背景影片素材 | 已整合 | `VECTEEZY_API_KEY` in `.env` |
| **matplotlib** | 財經圖表生成（深色專業風格，1080×1920） | 已整合 | — |
| **YouTube Data API v3** | 影片上傳（OAuth2） | 已整合 | `config/client_secret.json` |
| **FFmpeg / FFprobe** | 影片剪輯、縮放、字幕燒錄、音訊合併 | 已整合 | 系統環境 |
| **Kling AI** | AI 影片生成（JWT 認證已測試） | 測試中 | `KLING_API_KEY/SECRET` in `.env` |
| **Firecrawl MCP** | 即時搜尋/擷取真實財經數據，防止 Gemini 憑記憶捏造數字 | 已整合 | Claude Code MCP server，無需 `.env` 設定 |

---

## 標準製作流程（4 個 Stage）

```bash
# 基本用法（positional 語法，向下相容）
python main.py "台積電最新財報分析"

# 新語法（--topic + 可選參數）
python main.py --topic "GTC Taipei 演講重點" --custom-photos "slot2:jensen.jpg"
```

### Stage 0 — 資料查證（Firecrawl，防止數字幻覺）

**職責分離：Firecrawl 負責數字正確性，Gemini 只負責文案撰寫。**
Gemini 2.5 Flash 沒有即時資料，若直接要求它「生成財報數字」必然依賴訓練資料或憑空
捏造。為避免此風險，具體數字一律先由 Firecrawl 查證，Gemini 只把已驗證的數字寫成
有起承轉合的旁白。

**完整流程：**
1. 決定本集主題（例：「台積電 2026Q1 財報分析」）
2. 用 Firecrawl MCP 工具（`firecrawl_search` / `firecrawl_scrape` / `firecrawl_extract`）
   抓取公開財報、法說會新聞、股價等真實資料 —— 這一步發生在對話層（Claude Code
   agent 手動執行），不是 Python pipeline 裡的程式碼
3. 把抓到的資料整理成條列文字，寫入專案根目錄 `research_data.txt`
4. 執行 `python main.py "主題"` → Stage 1 自動讀取 `research_data.txt`
5. `content_gen.py` 把內容塞進 Gemini prompt 的 `{research}` 區塊，並附上規則：
   - 只能使用 `research_data.txt` 裡的數字，禁止使用訓練資料或記憶中的舊數字
   - 查無資料的項目一律用質化描述帶過（例如「本季獲利表現穩健」），絕不可捏造
   - `chart_data` 每個數值都要對應到 `research_data.txt`，對不上就留空陣列 `[]`
6. 完成後刪除 `research_data.txt`（同 `custom_narration.txt` 慣例，避免影響下次執行）

`research_data.txt` 不存在時：Gemini 會收到「未提供已驗證研究資料，禁止捏造具體
數字」的提示，旁白全部改用質化描述——安全網會擋下假數字，但也代表這支影片不會有
具體財報數字，請務必先完成這一步再製作財報類影片。

> 補充（2026-07-04 查證）：`scripts/content_gen.py` 呼叫 Gemini 時只設定
> `genai.types.GenerationConfig(response_mime_type="application/json")`（JSON mode），
> **沒有設定任何 `tools=[...]` 或 Google Search grounding 工具**，程式碼層級確認未使用
> Gemini 內建 grounding，與上述「Gemini 只負責文案撰寫」的原則一致。

---

### Stage 1 — 腳本生成 (`scripts/content_gen.py`)

- 若 `custom_narration.txt` 存在 → 使用手動旁白，AI 僅補充 title / search_queries / hashtags
- 否則 → 讀取 `research_data.txt`（見 Stage 0），連同主題一起交給 Gemini 2.5 Flash 生成完整腳本
  - `research_data.txt` 不存在時，Gemini 改用質化描述，不會捏造具體數字
- Gemini 呼叫：JSON mode（`response_mime_type=application/json`）+ retry 3 次（指數退避 2s/4s）
- 必填欄位驗證（title / narration / search_queries）：缺漏或型別錯誤時套用安全預設值，不中斷 pipeline
- 輸出：`output/<id>/script.json`

**旁白命名規則（prompt 內建）：**
- 禁止使用「老黃」稱呼 NVIDIA 執行長
- 統一使用「Jensen Huang」（第一次）、「Jensen」（後續）

**腳本 JSON 結構：**
```json
{
  "title": "影片標題（15字內）",
  "narration": "繁體中文旁白（300-400字，約60秒）",
  "visual_prompts": ["scene 1: ...", "scene 2: ...", "scene 3: ..."],
  "search_queries": [
    "stock market candlestick chart",
    "AI processor technology",
    "semiconductor chip manufacturing",
    "... 共10個英文關鍵字 ..."
  ],
  "chart_data": {
    "company": "公司名稱",
    "currency": "NTD 或 USD",
    "unit": "億 或 百萬",
    "quarters": ["2024Q1", "2024Q2", "2024Q3", "2024Q4"],
    "revenue": [...],
    "gross_margin": [...],
    "net_profit": [...],
    "eps": [...],
    "yoy_growth": [...],
    "segments": {"HPC": 52, "Smartphone": 33, ...}
  },
  "hashtags": ["#財經", "#投資", "#Shorts"]
}
```

---

### Stage 2 — TTS 配音 (`scripts/tts.py`)

**逐句精準同步流程（2026-06 重構）：**

1. `_split_sentences()` — 旁白依 `。！？` 拆成句子清單
2. 每句分別呼叫 Edge TTS 產生獨立 MP3 暫存檔
3. **ffprobe 量測每句的實際時長**（非估算）
4. ffmpeg concat 拼接所有片段為 `narration.mp3`
5. `_build_srt_from_segments()` — 累計真實時長建 SRT，長句用 `_display_split()` 切成兩行

每個字幕條目的開始／結束時間完全對應音訊，消除估算誤差。

- 語音：`zh-TW-HsiaoChenNeural`，語速 `+5%`
- 數字處理：`%` 自動轉為「百分之N」
- 短條目（< 1.5s）自動合併至相鄰條目

---

### Stage 3 — 背景素材（7 個 Slot）

**題材類型自動判斷（`detect_content_type()`）：**

| 類型 | 觸發條件 | Slot 配置 |
|---|---|---|
| `earnings` | topic/narration 含財報關鍵字，且 chart_data 有 revenue | 2 圖表 + 5 影片 |
| `market` | topic/narration 含大盤/週報/Computex 等市場關鍵字，或無法判斷 | 1 圖表 + 6 影片 |
| `education` | topic/narration 含如何/教學/入門等學習關鍵字 | 3 圖表 + 4 影片 |

**Slot 配置詳細：**

```
earnings（7 slots）:
  1:pexels  2:chart  3:pixabay  4:chart  5:mixkit  6:vecteezy  7:pexels

market（7 slots）:
  1:pexels  2:pixabay  3:chart  4:mixkit  5:vecteezy  6:pexels  7:pixabay

education（7 slots）:
  1:pexels  2:chart  3:pixabay  4:chart  5:mixkit  6:chart  7:vecteezy
```

**3a — 影片素材 (`video_gen.py`)：**
- 4 個來源輪替：Pexels API / Pixabay API / Mixkit CDN 爬蟲 / Vecteezy API
- 每段裁剪至最長 25 秒，重新編碼至 1080×1920 / 30fps / yuv420p
- `seen_ids` set 防止同影片重複；搜尋無結果自動 fallback 通用關鍵字

**3b — matplotlib 圖表 (`chart_gen.py`)：**

| 圖表類型 | 函式 | 觸發時機 |
|---|---|---|
| `revenue_bar` | `generate_finance_chart()` | earnings，有 chart_data |
| `gross_margin` | `generate_finance_chart()` | earnings，有 chart_data |
| `eps_trend` | `generate_finance_chart()` | earnings，有 chart_data |
| `candlestick` | `generate_finance_chart()` | earnings，有 chart_data |
| `segment_bar` | `generate_finance_chart()` | earnings，有 chart_data |
| 台積電股價走勢 | `generate_market_chart()` | narration 含「台積電」或「台股」 |
| 大盤指數變化 | `generate_market_chart()` | 其他 market 題材 |

圖表規格：1080×1920（6×10.67 英吋，180 DPI）、深色主題（背景 `#0d1117`）、Ken Burns zoom → 5 秒 MP4

**3c — 自訂照片 (`photo_gen.py`)：**

把照片放入 `assets/custom/`，製作時用 `--custom-photos` 指定：

```bash
python main.py --topic "主題" --custom-photos "slot2:photo1.jpg,slot4:photo2.jpg"
```

| 照片比例 | 處理方式 |
|---|---|
| 橫式（w/h > 9/16） | 模糊版填滿背景 + 清晰版置中疊加，消除黑邊 |
| 直式（w/h ≤ 9/16） | 縮放至適合，四周補黑邊 |
| 兩者 | 套用 Ken Burns 緩慢放大（1x → 1.15x），輸出 5 秒 MP4 |

找不到指定照片時：log 顯示警告，自動 fallback 至素材庫，不中斷流程。

---

### Stage 4 — 合成最終影片 (`scripts/assembler.py`)

1. 7 段 clip 串接為 background.mp4
2. 循環（tile）至覆蓋完整音訊時長，ultrafast 預編碼暫存 `.tiled.mp4`
3. scale 至 1080×1920，黑邊 letterbox 補足
4. 燒錄字幕：Noto Sans CJK TC Bold 24px，白字黑邊，底部 80px
5. 合併音訊 AAC 128k，H.264 fast preset，yuv420p
6. 清除 `.tiled.mp4` 暫存
- 輸出：`output/<id>/final.mp4`

---

## 輸出格式規格

| 項目 | 規格 |
|---|---|
| 解析度 | 1080 × 1920（9:16 直式） |
| 影格率 | 30 fps |
| 影片編碼 | H.264 (libx264)，fast preset，yuv420p |
| 音訊編碼 | AAC 128 kbps |
| 目標時長 | ~60 秒（依 TTS 實際長度） |
| 配音語言 | 繁體中文（台灣腔，zh-TW-HsiaoChenNeural +5%） |
| 字幕 | 燒錄進影片，Noto Sans CJK TC Bold 24px，底部 80px |
| 平台 | YouTube Shorts |

---

## 常用指令備忘

```bash
# 啟動虛擬環境（WSL）
source venv/bin/activate

# ── 基本製作 ──────────────────────────────────────────────────────────────
python main.py "台積電最新財報分析"
python main.py "輝達 NVDA Q1 財報"
python main.py --topic "GTC Taipei 演講重點及對台股後續影響"

# ── 使用自訂旁白 ──────────────────────────────────────────────────────────
# 建立旁白檔案後執行，完成後刪除（不刪會影響下次）
cat > custom_narration.txt << 'EOF'
Jensen Huang 昨天在台北說了什麼？...
EOF
python main.py "主題名稱"
rm custom_narration.txt

# ── 使用 Firecrawl 已驗證財經資料（防止數字幻覺，財報類影片建議必做）──────────
# 1. 先用 Firecrawl MCP 工具抓取真實數字，整理成條列文字寫入 research_data.txt
cat > research_data.txt << 'EOF'
- 營收：新台幣592億元，年增3.2%（來源：公開財報 2026Q1）
- 毛利率：53.1%
- EPS：8.7元
- 法說會重點：下季展望維持審慎樂觀
EOF
# 2. 製作時 Stage 1 會自動讀取，Gemini 只會用這些數字撰寫文案
python main.py "台積電 2026Q1 財報分析"
# 3. 完成後刪除，避免影響下次執行
rm research_data.txt

# ── 插入自訂照片 ──────────────────────────────────────────────────────────
# 1. 把照片放進 assets/custom/
cp ~/Downloads/jensen.jpg assets/custom/
# 2. 製作時指定 slot（1~7）
python main.py --topic "主題" --custom-photos "slot2:jensen.jpg,slot5:chart.png"

# ── 查看輸出與日誌 ────────────────────────────────────────────────────────
ls -lt /mnt/d/yt-shorts-finance/output/ | head -5
tail -f logs/pipeline.log

# ── 元件測試 ──────────────────────────────────────────────────────────────
python test_gemini.py
python test_tts.py
python test_video_gen.py

# ── 環境檢查 ──────────────────────────────────────────────────────────────
ffmpeg -version && ffprobe -version
python -c "import matplotlib; print(matplotlib.__version__)"
```

---

## 環境設定注意事項

- API 金鑰存於 `config/.env`，**不可提交至 git**
- 字幕字型需安裝：`sudo apt install fonts-noto-cjk`
- FFmpeg 需支援 libx264：`sudo apt install ffmpeg`
- Python venv 已建立（`source venv/bin/activate` 啟動）
- YouTube 上傳需先完成 OAuth 授權（`config/client_secret.json`）
- Vecteezy API key 需加入 `config/.env`（`VECTEEZY_API_KEY=...`）
- Mixkit 爬蟲依賴 CDN URL regex，若 Mixkit 改版可能需更新 `video_gen.py` 的 patterns

---

## 已知問題與解法

### 問題：分段輸出後在剪輯軟體合成，接縫處配音重疊

**現象**
把各 clip 分段輸出（每段含配音），
在 CapCut 等剪輯軟體依序拼接後，
片段接續處的語音會有些微重疊，聽起來不自然。

**根因**
MP3/AAC 編碼在每段音訊的開頭和結尾都有 padding，
分段輸出時每段各自包含一段配音，
21 個片段接起來就會累積出可感知的重疊。

**正確做法（分段輸出時必須遵守）**
1. 輸出「無聲」的影片片段（只有畫面和字幕）
   檔名格式：clip_XX_mute.mp4
   輸出路徑：output/[專案名]_segments/mute/

2. 另外輸出一個「完整連續配音」音檔
   檔名：narration_full.mp3
   整支影片的旁白一氣呵成，不切割

3. 使用者在剪輯軟體的操作：
   - 21 個無聲片段依序拼接
   - narration_full.mp3 放到音軌
   - 配音連續，無接縫問題

**裁切注意事項**
裁切片段時不可用 -c:v copy（stream copy），
因為 stream copy 只能在關鍵影格處切，
會導致總長度與旁白不符（實測誤差達 1.57 秒）。
必須重新編碼裁切（-t 精準卡在指定時長），
誤差可控制在 0.4 秒內（分散在各段，無感知）。
- 輸出路徑：`/mnt/d/yt-shorts-finance/output/`(D 槽)
