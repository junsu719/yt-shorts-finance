# DECISIONS.md — stocks500yt / yt-shorts-finance

## 2026-07-04 — 聖經範本部署到專案 CLAUDE.md

**決策**:將 `~/claude-bible/projects/stocks500yt.md`(聖經範本)合併到
`~/yt-shorts-finance/CLAUDE.md` 最上方,原有 16KB 技術規格書完整保留在後面
(標題改為「YT Shorts Finance — 繁體中文財經短影音自動化系統(技術規格書)」)。
原檔備份於 `CLAUDE.md.bak-20260704`。

**背景**:Jun 詢問合併前是否已記載 research_data.txt / Firecrawl grounding 架構、
以及聖經範本「架構地圖」段落是否有遺漏或矛盾。兩次 AskUserQuestion 詢問處理方式
皆逾時無回應,依鐵律/身分規範第1條(小決策自行選擇最符合規範方案,記入
DECISIONS.md,關卡時一次匯報)採用風險最低的合併方案(不覆蓋任何既有內容)。

**查證結果(有證據,非猜測)**:
1. research_data.txt 架構已完整記載於技術規格書 Stage 0,比聖經範本詳細。
2. 現有文件沒有出現「grounding」字樣,未明文寫「已撤銷 Gemini grounding」。
   但查 `scripts/content_gen.py:261` 只設定
   `genai.types.GenerationConfig(response_mime_type="application/json")`,
   沒有任何 `tools=[...]` 或 Google Search grounding 設定 —— 程式碼證實未使用
   grounding,只是文件用詞不夠精確。已在合併後的 CLAUDE.md Stage 0 補一段
   查證註記。
3. 聖經範本「架構地圖」提到的 `scripts/slot_allocator.py`、
   `scripts/make_segments.py`、`steps/step2_charts.py` 確實存在於 repo,但技術
   規格書完全沒提及。查證發現:
   - `main.py:21` 有 `from scripts.slot_allocator import build_slot_plan,
     print_slot_table` → slot_allocator **已整合進主產線**,技術規格書 Stage 3
     漏寫。
   - `main_confirm.py` 完整依賴 `steps/step1_script.py` ~ `steps/step5_upload.py`
     (5 個 import,53/75/107/130/154 行)—— 這是一套完全獨立、目前**沒有任何
     文件描述**的互動模式後端。
   - 另外還有根目錄 `make_segments.py`(16:9 長片工具,與 `scripts/make_segments.py`
     不同檔案)、`stage2_risk_edu_tts.py` / `stage3_risk_edu_assets.py` /
     `stage4_risk_edu_segments.py` / `diagnose_clips.py` 等模組,同樣完全未被
     任何 CLAUDE.md 記載。

**待辦(尚未處理,下次 session 或 Jun 指定時處理)**:
- [ ] 確認 `main_confirm.py` + `steps/` 這套互動模式後端是否為現役,若是則補寫完整
      文件到 CLAUDE.md
- [ ] 確認根目錄 `make_segments.py`(16:9 長片)與 `stage2~4_risk_edu_*.py` /
      `diagnose_clips.py` 是現役工具還是實驗殘留物,現役則補文件、殘留則考慮清理
- [ ] 若上述確認為現役,聖經範本 `~/claude-bible/projects/stocks500yt.md` 的
      「架構地圖」段落也要一併修正/擴充,目前只有一行原則帶過,細節不足

## 2026-07-06 — 新增「兩檔股票對比」圖表能力(diverging bar 補 watermark)

**任務**:製作「鴻海、大立光6月營收出爐」影片,Jun 要求圖表顯示兩家公司 6月營收
年增率對比(鴻海 +52.11%、大立光 -10.46%),鴻海綠色、大立光紅色,並標註
「資料來源:公開資訊觀測站 2026/07/05」。

**問題**:既有 `_anim_vertical_bar()`(Jun 訊息中所稱的「vertical_bar_chart()」)在
`bar.set_height(max(val*frac, 0.0))` 這行會把負值強制夾到 0 —— 若直接套用,大立光
的下跌長條會顯示成一條貼齊 0 的空柱,完全看不出「跌到谷底」的視覺重點。改用
`_anim_diverging_bar()`(既有的第三種動畫模板,原本就會依正負值自動上色綠/紅、
負值正確往下延伸)才能正確呈現這支影片的核心對比。

**決策**:
1. 判斷 Jun 指定的模板名稱是字面理解錯誤(她只知道「三種模板」的概念,不清楚
   `vertical_bar` 無法畫負值),依鐵律第1條實作層級小決策自行選用能正確呈現資料的
   `diverging_bar`,不中途詢問。
2. `_anim_diverging_bar()` 原本沒有 watermark 參數(另外兩種動畫模板都有),補上
   `watermark_text: str = ""`(預設空字串,向下相容),並在 `generate_animated_chart()`
   的 `gross_margin` 分支讓 `chart_data.chart_title` / `chart_data.chart_watermark`
   可覆寫預設標題與浮水印 —— 這樣未來任何「兩家公司對比」題材都能重複使用,不用
   每次都寫死。
3. 為了讓這支影片只出現這一張對比圖(而非 earnings 題材預設的 2 圖表 slot),narration
   只放 1 個 `[CHART1]` 標記 —— `slot_allocator.py` 是依實際標記數量動態分配 slot,
   不是寫死題材數量,所以這樣做不會影響其他既有影片的 slot 邏輯。
4. 為了讓這唯一一個圖表 slot 100% 選到 `gross_margin`(而非隨機洗牌到
   revenue_bar/eps_trend/segment_bar 等會用到空陣列預設假資料的類型),寫了一次性
   驅動腳本 `_run_honghai_largan.py`,執行時強制 `main.CHART_TYPES = ["gross_margin"]`
   後呼叫 `main.run()`。腳本與 `custom_script.json` 皆已在產出後刪除,不留在 repo。

**產出**:`/mnt/d/yt-shorts-finance/output/1783325874/final.mp4`(88秒,1080×1920)。

**沿用程式碼變更(保留,非一次性)**:`scripts/chart_gen.py` 的
`_anim_diverging_bar()` watermark 參數 + `generate_animated_chart()` 的
`chart_title`/`chart_watermark` 覆寫邏輯。
