# YT Shorts Finance

繁體中文財經短影音自動化系統。輸入主題字串，自動生成可上傳至 YouTube Shorts 的直式短影音（1080×1920、含燒錄字幕、繁中配音）。

## 功能

- **AI 腳本生成**：Gemini 2.5 Flash 全自動生成繁體中文財報分析旁白、視覺提示詞、hashtag
- **TTS 配音**：Edge TTS（`zh-TW-HsiaoChenNeural`）逐句合成，ffprobe 精準對齊字幕
- **背景素材**：Pexels / Pixabay / Mixkit / Vecteezy 四源輪替下載影片素材
- **財經圖表**：matplotlib 深色主題圖表（營收、毛利率、EPS、K線等）轉 Ken Burns 動態 MP4
- **自訂照片**：插入個人照片並套用 Ken Burns 效果
- **自動合成**：FFmpeg 燒錄字幕（Noto Sans CJK TC）、混音、輸出 H.264 MP4
- **YouTube 上傳**：YouTube Data API v3 OAuth2 自動上傳

## 輸出規格

| 項目 | 規格 |
|------|------|
| 解析度 | 1080 × 1920（9:16） |
| 影格率 | 30 fps |
| 影片編碼 | H.264，yuv420p |
| 音訊編碼 | AAC 128 kbps |
| 目標時長 | ~60 秒 |
| 配音語言 | 繁體中文（台灣腔） |

## 安裝

### 系統需求

```bash
# Ubuntu / WSL
sudo apt install ffmpeg fonts-noto-cjk
```

確認 FFmpeg 支援 libx264：

```bash
ffmpeg -version | grep libx264
```

### Python 環境

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 環境設定

```bash
# 1. 建立設定資料夾與金鑰檔
mkdir -p config
cp .env.example config/.env
# 用文字編輯器填入各 API 金鑰
nano config/.env

# 2. YouTube OAuth 憑證（從 Google Cloud Console 下載）
# 放置路徑：config/client_secret.json
```

## 使用方式

```bash
source venv/bin/activate

# 基本用法
python main.py "台積電最新財報分析"
python main.py "輝達 NVDA Q1 財報"

# 指定主題
python main.py --topic "GTC Taipei 演講重點及對台股後續影響"

# 手動覆蓋旁白（建立旁白檔案後執行）
cat > custom_narration.txt << 'EOF'
Jensen Huang 昨天在台北說了什麼？...
EOF
python main.py "主題名稱"
rm custom_narration.txt  # 用完記得刪除

# 插入自訂照片（放入 assets/custom/ 後指定 slot）
python main.py --topic "主題" --custom-photos "slot2:jensen.jpg,slot5:chart.png"
```

輸出影片位於 `output/<unix_timestamp>/final.mp4`。

## API 金鑰申請

| 金鑰 | 用途 | 取得位置 |
|------|------|----------|
| `GEMINI_API_KEY` | 腳本生成 + Imagen 3 圖像 | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `KLING_API_KEY` / `KLING_API_SECRET` | AI 影片生成（測試中） | [Kling AI 開發者平台](https://klingai.com/dev) |
| `PEXELS_API_KEY` | 背景影片素材 | [Pexels API](https://www.pexels.com/api/) |
| `PIXABAY_API_KEY` | 背景影片素材 | [Pixabay API](https://pixabay.com/api/docs/) |
| `VECTEEZY_API_KEY` | 背景影片素材 | [Vecteezy Developers](https://www.vecteezy.com/developers) |
| YouTube OAuth | 影片上傳 | [Google Cloud Console](https://console.cloud.google.com/)（建立 OAuth 2.0 用戶端 ID） |

## 資料夾結構

```
yt-shorts-finance/
├── main.py                   # 主程式（argparse CLI + 4 段 pipeline）
├── scripts/
│   ├── content_gen.py        # Stage 1：Gemini 腳本生成
│   ├── tts.py                # Stage 2：Edge TTS 配音 + SRT 字幕
│   ├── video_gen.py          # Stage 3a：背景影片下載
│   ├── chart_gen.py          # Stage 3b：matplotlib 財經圖表
│   ├── photo_gen.py          # Stage 3c：自訂照片處理
│   ├── image_gen.py          # Stage 3d：Imagen 3 AI 圖像
│   └── assembler.py          # Stage 4：FFmpeg 合成
├── assets/
│   ├── custom/               # 自訂照片放這裡（--custom-photos）
│   ├── images/               # 圖片暫存
│   ├── subtitles/            # SRT 字幕暫存
│   └── video/                # 下載的背景素材
├── output/                   # 輸出影片（每次獨立資料夾）
├── config/                   # API 金鑰（不提交 git）
│   ├── .env
│   └── client_secret.json
└── .env.example              # 環境變數範本
```

## 注意事項

- `config/` 資料夾含 API 金鑰，**不可提交至 git**
- `output/` 資料夾含影片檔案，建議加入 `.gitignore`
- Mixkit 素材透過 CDN 爬蟲取得，無需 API 金鑰
- YouTube 上傳首次需完成 OAuth 瀏覽器授權流程
