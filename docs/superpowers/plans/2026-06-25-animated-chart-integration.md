# Animated Chart Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace static PNG chart slots in the main Shorts pipeline with animated MP4 charts, keeping the assembler unchanged.

**Architecture:** Add portrait-format animated chart functions (`_anim_vertical_bar`, `_anim_horizontal_bar`, `_anim_diverging_bar`) directly to `chart_gen.py`; expose `generate_animated_chart()` and `generate_animated_market_chart()` as the new public API. Update `main.py` to call the animated API (skipping the old PNG→`chart_to_clip` hop). Update `step4_compose.py` to accept MP4 charts via `VideoFileClip`.

**Tech Stack:** matplotlib FuncAnimation, FFMpegWriter (libx264, yuv420p), ffprobe, moviepy VideoFileClip

---

### Task 1: Add animated chart functions to scripts/chart_gen.py

**Files:**
- Modify: `scripts/chart_gen.py`

- [ ] Add `import matplotlib.animation as animation` at top
- [ ] Add `_ease_out`, `_ease_in_out`, `_anim_writer`, `_portrait_fig` helpers
- [ ] Add `_anim_vertical_bar(data, labels, title, unit, color, output_path, duration=6)`  
      Portrait 1080×1920, 6s/180f: axes→bars grow→numbers count→trend line
- [ ] Add `_anim_horizontal_bar(data, labels, title, highlight_index, unit, output_path, duration=5)`  
      Portrait 1080×1920, 5s/150f: bars extend→numbers→annotation fly-in
- [ ] Add `_anim_diverging_bar(data, labels, title, unit, output_path, duration=7)`  
      Portrait 1080×1920, 7s/210f: zero axis→neg bars down→pos bars up→blink annotation
- [ ] Add `generate_animated_chart(chart_data, chart_type, output_path, duration=6)`  
      Routes: eps_trend/candlestick→vertical, segment_bar→horizontal, revenue_bar/gross_margin→vertical or diverging
- [ ] Add `generate_animated_market_chart(narration, output_path, duration=6)`  
      Same logic as `generate_market_chart` but outputs animated MP4

### Task 2: Update main.py chart slot to use animated output

**Files:**
- Modify: `main.py` (lines ~233–274)

- [ ] Import `generate_animated_chart, generate_animated_market_chart` from scripts.chart_gen
- [ ] In chart slot block, replace `chart_png` temp file + `chart_to_clip()` with direct `generate_animated_chart(chart_data, chart_type, clip_path)`
- [ ] Replace `generate_market_chart(...) + chart_to_clip(...)` fallback with `generate_animated_market_chart(..., clip_path)`
- [ ] Keep education chart path unchanged (still uses `generate_education_chart + chart_to_clip`)

### Task 3: Update steps/step4_compose.py for MP4 charts

**Files:**
- Modify: `steps/step4_compose.py` lines 84–100, 129–137

- [ ] In `_resolve_chart_path()`: expand fallback dict to also look for `.mp4` variants
- [ ] In `_compose_with_moviepy()`: branch on file extension — `.mp4` → `VideoFileClip(...).subclipped(0, duration)`, `.png` → `ImageClip(...).with_duration(duration)`

### Task 4: Integration test

- [ ] Create `custom_script.json` with `chart_data` containing EPS test data
- [ ] Run pipeline: `python main.py --topic "測試動畫圖表整合"`
- [ ] Verify with ffprobe that chart slots in final.mp4 contain animation frames (not static)
- [ ] Delete `custom_script.json`
