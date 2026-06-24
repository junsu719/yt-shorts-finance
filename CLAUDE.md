# YT Shorts Finance — 繁體中文財經短影音自動化系統

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

---

## 標準製作流程（4 個 Stage）

```bash
# 基本用法（positional 語法，向下相容）
python main.py "台積電最新財報分析"

# 新語法（--topic + 可選參數）
python main.py --topic "GTC Taipei 演講重點" --custom-photos "slot2:jensen.jpg"
```

### Stage 1 — 腳本生成 (`scripts/content_gen.py`)

- 若 `custom_narration.txt` 存在 → 使用手動旁白，AI 僅補充 title / search_queries / hashtags
- 否則 → Gemini 2.5 Flash 全自動生成完整腳本
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
- 輸出路徑：`/mnt/d/yt-shorts-finance/output/`（D 槽）
