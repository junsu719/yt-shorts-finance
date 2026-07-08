#!/usr/bin/env python3
"""Stage 3 — Download 20 video clips + generate 3 landscape chart animations.

Output directory: /mnt/d/yt-shorts-finance/output/risk_education_segments/
Naming:  clip_01.mp4 … clip_23.mp4  (slot index, including chart slots)
"""
import json
import math
import sys
import time
from pathlib import Path

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as _manim
from matplotlib import font_manager as _fm
from matplotlib.font_manager import FontProperties
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from scripts.slot_allocator import build_slot_plan
from scripts.video_gen import fetch_clip

OUT_DIR    = Path("/mnt/d/yt-shorts-finance/output/risk_education_segments")
SCRIPT_P   = OUT_DIR / "script.json"
SRT_P      = str(OUT_DIR / "narration.srt")
CHARTS_P   = str(OUT_DIR / "narration_charts.json")

W, H, FPS = 1920, 1080, 30   # landscape

# ── CJK font setup (matches chart_gen.py pattern) ────────────────────────────
_CJK_FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]
_CJK_PATH: str | None = next((p for p in _CJK_FONT_PATHS if os.path.exists(p)), None)
if _CJK_PATH:
    _fm.fontManager.addfont(_CJK_PATH)
    matplotlib.rcParams["font.family"] = "Noto Sans CJK JP"

# Per-element FontProperties used for explicit text nodes (title, labels, annotations)
FONT_PROP = FontProperties(fname=_CJK_PATH) if _CJK_PATH else FontProperties()


def _fp(size: int = 12, bold: bool = False) -> FontProperties:
    """Return Noto CJK FontProperties at the requested size/weight."""
    fp = FontProperties(fname=_CJK_PATH) if _CJK_PATH else FontProperties()
    fp.set_size(size)
    fp.set_weight("bold" if bold else "regular")
    return fp


# ── Chart style (matches chart_gen.py palette) ───────────────────────────────
_BG    = "#0d1117"
_TEXT  = "#e6edf3"
_GRAY  = "#8b949e"
_GREEN = "#2ea043"
_RED   = "#f85149"
_BLUE  = "#58a6ff"
_YELLOW = "#d29922"


def _landscape_fig():
    """Return (fig, ax) at 1920×1080, dark theme."""
    fig, ax = plt.subplots(figsize=(16, 9), dpi=120)   # 16*120=1920, 9*120=1080
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(_GRAY)
    ax.spines["bottom"].set_color(_GRAY)
    ax.tick_params(colors=_GRAY, length=4)
    return fig, ax


def _writer():
    return _manim.FFMpegWriter(fps=FPS, codec="libx264",
                                extra_args=["-pix_fmt", "yuv420p"])


def _ease(t: float) -> float:
    return 1 - (1 - t) ** 3


# ── Landscape diverging bar (CHART1, CHART2) ─────────────────────────────────

def _make_diverging(spec: dict, output_path: str, duration: int = 8) -> None:
    """Animated landscape diverging bar chart.

    spec keys: data, labels, title, unit
    Animation phases (TOTAL = duration*FPS frames):
      0   → 20%  : zero axis draws L→R
      20% → 60%  : negative bars grow downward
      60% → 100% : positive bars grow upward + value labels
    """
    data   = spec["data"]
    labels = spec["labels"]
    title  = spec["title"]
    unit   = spec["unit"]
    n      = len(data)
    TOTAL  = duration * FPS

    abs_max = max(abs(v) for v in data) * 1.35 or 1.0
    neg_idx = [i for i, v in enumerate(data) if v < 0]
    pos_idx = [i for i, v in enumerate(data) if v >= 0]

    P1 = int(TOTAL * 0.20)   # zero axis done
    P2 = int(TOTAL * 0.60)   # negatives done
    P3 = TOTAL               # positives + labels done

    fig, ax = _landscape_fig()
    ax.set_xlim(-0.55, n - 0.45)
    ax.set_ylim(-abs_max, abs_max)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels)
    for t in ax.get_xticklabels():
        t.set_fontproperties(_fp(14))
        t.set_color(_TEXT)
    ax.set_yticks([])
    ax.set_title(title, fontproperties=_fp(22, bold=True), color=_TEXT, pad=20)

    zero_ln, = ax.plot([], [], color=_GRAY, linewidth=2, alpha=0.8)
    colors   = [_RED if v < 0 else _GREEN for v in data]
    bars     = ax.bar(range(n), [0.0]*n, color=colors, alpha=0.88,
                      width=0.55, edgecolor=_BG, linewidth=1)
    val_txts = [
        ax.text(i, 0, "", ha="center",
                va="top" if v < 0 else "bottom",
                color=_TEXT, fontproperties=_fp(16, bold=True))
        for i, v in enumerate(data)
    ]

    def _set_bar(i, frac):
        v = data[i]
        h = abs(v) * frac
        if v < 0:
            bars[i].set_y(-h); bars[i].set_height(h)
        else:
            bars[i].set_y(0);  bars[i].set_height(h)

    def update(frame):
        # Phase 1: zero axis
        prog = min(frame / max(P1, 1), 1.0)
        zero_ln.set_data([-0.5, -0.5 + prog * n], [0, 0])

        # Phase 2: negatives
        neg_dur = max(P2 - P1, 1) / max(len(neg_idx), 1)
        for j, i in enumerate(neg_idx):
            t0 = P1 + j * (neg_dur * 0.4)
            t1 = t0 + neg_dur
            frac = _ease(max(0, min((frame - t0) / max(t1 - t0, 1), 1.0)))
            _set_bar(i, frac)

        # Phase 3: positives
        pos_dur = max(P3 - P2, 1) / max(len(pos_idx), 1)
        for j, i in enumerate(pos_idx):
            t0 = P2 + j * (pos_dur * 0.4)
            t1 = t0 + pos_dur
            frac = _ease(max(0, min((frame - t0) / max(t1 - t0, 1), 1.0)))
            _set_bar(i, frac)

        # Value labels appear after each bar finishes
        for i, (txt, v) in enumerate(zip(val_txts, data)):
            if i in neg_idx:
                done = P1 + (neg_idx.index(i) + 1) * (max(P2 - P1, 1) / max(len(neg_idx), 1))
            else:
                done = P2 + (pos_idx.index(i) + 1) * (max(P3 - P2, 1) / max(len(pos_idx), 1))
            if frame >= done:
                sign = "+" if v >= 0 else ""
                txt.set_text(f"{sign}{v:,.0f}{unit}")
                off = abs_max * 0.05
                txt.set_position((i, v - off if v < 0 else v + off * 0.5))
            else:
                txt.set_text("")

    anim = _manim.FuncAnimation(fig, update, frames=TOTAL, interval=1000 / FPS)
    print(f"  → 儲存 {output_path} ...", flush=True)
    anim.save(output_path, writer=_writer())
    plt.close(fig)


# ── Landscape horizontal bar (CHART3) ────────────────────────────────────────

def _make_horizontal(spec: dict, output_path: str, duration: int = 8) -> None:
    """Animated landscape horizontal bar chart.

    spec keys: data, labels, title, highlight_index
    Animation: bars grow left→right staggered; highlight bar shown with accent color.
    """
    data            = spec["data"]
    labels          = spec["labels"]
    title           = spec["title"]
    hi              = spec.get("highlight_index", -1)
    n               = len(data)
    TOTAL           = duration * FPS
    max_val         = max(data) * 1.2 or 1.0

    stagger = TOTAL // (n + 2)

    colors = []
    for i in range(n):
        if i == hi:
            colors.append(_BLUE)
        elif data[i] == max(data):
            colors.append(_GREEN)
        else:
            colors.append(_GRAY)

    fig, ax = _landscape_fig()
    ax.set_xlim(0, max_val)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels[::-1])
    for t in ax.get_yticklabels():
        t.set_fontproperties(_fp(14))
        t.set_color(_TEXT)
    ax.set_xticks([])
    ax.set_title(title, fontproperties=_fp(22, bold=True), color=_TEXT, pad=20)
    ax.invert_yaxis()

    bars = ax.barh(range(n), [0.0]*n, color=colors[::-1], alpha=0.88,
                   height=0.55, edgecolor=_BG, linewidth=1)
    val_txts = [
        ax.text(0, i, "", va="center", ha="left",
                color=_TEXT, fontproperties=_fp(16, bold=True))
        for i in range(n)
    ]
    # Highlight annotation
    hi_anno = ax.text(
        0, hi, "", va="center", ha="right",
        color=_BLUE, fontproperties=_fp(13, bold=True), visible=False,
    )

    reversed_data = data[::-1]
    reversed_colors = colors[::-1]

    def update(frame):
        for i in range(n):
            t0   = stagger * i
            t1   = t0 + stagger * 1.5
            frac = _ease(max(0, min((frame - t0) / max(t1 - t0, 1), 1.0)))
            w    = reversed_data[i] * frac
            bars[i].set_width(w)
            if frame >= t1:
                val_txts[i].set_text(f"{reversed_data[i]}%")
                val_txts[i].set_x(w + max_val * 0.01)
            else:
                val_txts[i].set_text("")

        # Highlight annotation for the "可投資金額" bar
        hi_bar_row = n - 1 - hi   # inverted axis
        done_hi = stagger * hi_bar_row + stagger * 1.5
        if frame >= done_hi:
            hi_anno.set_visible(True)
            bar_w = reversed_data[hi_bar_row] * 1.0
            hi_anno.set_position((bar_w + max_val * 0.18, hi_bar_row))
            hi_anno.set_text("← 只用這部分投資")
        else:
            hi_anno.set_visible(False)

    anim = _manim.FuncAnimation(fig, update, frames=TOTAL, interval=1000 / FPS)
    print(f"  → 儲存 {output_path} ...", flush=True)
    anim.save(output_path, writer=_writer())
    plt.close(fig)


# ── Chart dispatcher ──────────────────────────────────────────────────────────

_CHART_MAKERS = {
    "diverging_bar":  _make_diverging,
    "horizontal_bar": _make_horizontal,
}

# Map chart marker → which slot index it lands on (populated at runtime)
# key="CHART1", value=slot_index (1-based)
def _chart_marker_to_slot(slot_plan) -> dict[str, int]:
    chart_counter = 0
    result = {}
    for spec in slot_plan:
        if spec.type == "chart":
            chart_counter += 1
            result[f"CHART{chart_counter}"] = spec.index
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    script         = json.loads(SCRIPT_P.read_text(encoding="utf-8"))
    search_queries = script.get("search_queries", [])
    risk_charts    = script.get("risk_edu_charts", {})

    slot_plan = build_slot_plan(SRT_P, CHARTS_P, search_queries, "education")
    marker_to_slot = _chart_marker_to_slot(slot_plan)

    total   = len(slot_plan)
    n_video = sum(1 for s in slot_plan if s.type == "video")
    n_chart = sum(1 for s in slot_plan if s.type == "chart")

    print(f"Slot 總計：{total}（影片 {n_video} + 圖表 {n_chart}）")
    print(f"輸出目錄：{OUT_DIR}")
    print()

    seen_ids:    set[str] = set()
    seen_hashes: set[str] = set()
    summary: list[dict]  = []

    chart_counter = 0

    for spec in slot_plan:
        out_path = str(OUT_DIR / f"clip_{spec.index:02d}.mp4")
        label    = f"[{spec.index:02d}/{total}]"

        if spec.type == "video":
            t0 = time.time()
            try:
                fetch_clip(
                    spec.query, out_path,
                    source=spec.source,
                    seen_ids=seen_ids,
                    seen_hashes=seen_hashes,
                    clip_duration=spec.duration,
                    width=W, height=H,
                )
                elapsed = time.time() - t0
                print(f"  {label} video [{spec.source:8s}] {spec.duration:.1f}s  "
                      f"query='{spec.query}'  ({elapsed:.1f}s)")
                summary.append({
                    "slot": spec.index, "type": "video",
                    "source": spec.source, "duration": spec.duration,
                    "query": spec.query, "file": f"clip_{spec.index:02d}.mp4",
                })
            except Exception as e:
                print(f"  {label} ERROR: {e}")
                summary.append({
                    "slot": spec.index, "type": "video",
                    "source": spec.source, "duration": spec.duration,
                    "query": spec.query, "file": "ERROR",
                })

        else:  # chart
            chart_counter += 1
            marker = f"CHART{chart_counter}"
            spec_c = risk_charts.get(marker, {})
            chart_type = spec_c.get("type", "diverging_bar")
            maker  = _CHART_MAKERS.get(chart_type)
            t0 = time.time()
            try:
                maker(spec_c, out_path, duration=int(round(spec.duration)))
                elapsed = time.time() - t0
                print(f"  {label} CHART [{marker}] {spec.duration:.1f}s  "
                      f"type={chart_type}  ({elapsed:.1f}s)")
                summary.append({
                    "slot": spec.index, "type": "chart",
                    "marker": marker, "chart_type": chart_type,
                    "duration": spec.duration, "file": f"clip_{spec.index:02d}.mp4",
                })
            except Exception as e:
                print(f"  {label} CHART ERROR [{marker}]: {e}")
                summary.append({
                    "slot": spec.index, "type": "chart",
                    "marker": marker, "chart_type": chart_type,
                    "duration": spec.duration, "file": "ERROR",
                })

    # ── Summary table ─────────────────────────────────────────────────────────
    print()
    print("=" * 78)
    print(f"{'Slot':>4}  {'類型':6}  {'來源/圖表':12}  {'時長':6}  {'檔名':20}  查詢 / 說明")
    print("=" * 78)
    for r in summary:
        if r["type"] == "video":
            src  = r["source"]
            desc = r["query"][:32]
        else:
            src  = r["marker"]
            desc = r["chart_type"]
        dur  = f"{r['duration']:.1f}s"
        fn   = r["file"]
        print(f"  {r['slot']:02d}  {'video' if r['type']=='video' else 'CHART':6}  "
              f"{src:12}  {dur:6}  {fn:20}  {desc}")
    print("=" * 78)

    ok     = sum(1 for r in summary if r["file"] != "ERROR")
    errors = len(summary) - ok
    print(f"\n  完成：{ok}/{len(summary)} 個素材  |  失敗：{errors} 個")
    print(f"\n確認素材無誤後，執行 stage4_risk_edu_segments.py 合成各片段。")

    # Save summary for Stage 4
    (OUT_DIR / "assets_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
