"""Step 2：通用財務圖表動畫模板（MP4，1920×1080，30fps）

三種動畫函式：
  vertical_bar_chart    — 長條圖，6s，長條依序長出 + 趨勢線
  horizontal_bar_chart  — 橫向長條圖，5s，橫條延伸 + 標註框飛入
  diverging_bar_chart   — 正負長條圖，7s，零軸出現 → 負下正上 → 閃爍標註

generate_chart(chart_id, config) 保持與 main_confirm.py 的相容介面。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

# ── 路徑 ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
CHARTS_DIR = BASE_DIR / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# ── 顏色 ──────────────────────────────────────────────────────────────────────
BG       = "#1a1a2e"
GREEN    = "#00ff88"
RED      = "#ff4444"
GRAY     = "#888888"
WHITE    = "#ffffff"
DIMWHITE = "#cccccc"
YELLOW   = "#ffdd57"

# ── 字體 ──────────────────────────────────────────────────────────────────────
_CJK = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]
_FONT_PATH = next((p for p in _CJK if Path(p).exists()), None)
FONT_PROP  = FontProperties(fname=_FONT_PATH) if _FONT_PATH else FontProperties()

FPS = 30


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _writer() -> animation.FFMpegWriter:
    return animation.FFMpegWriter(
        fps=FPS,
        codec="libx264",
        extra_args=["-pix_fmt", "yuv420p"],
    )


def _ease_out(t: float) -> float:
    """Cubic ease-out：快出慢到"""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _ease_in_out(t: float) -> float:
    """Smoothstep：飛入效果"""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _fmt(val: float) -> str:
    """根據量級自動選擇小數位數"""
    if abs(val) >= 1000:
        return f"{val:,.0f}"
    if abs(val) >= 10:
        return f"{val:.1f}"
    return f"{val:.2f}"


def _base_fig() -> tuple:
    """回傳設定好基底樣式的 (fig, ax)"""
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_visible(False)
    return fig, ax


# ══════════════════════════════════════════════════════════════════════════════
# 圖表一：Vertical Bar Chart（長條圖，6秒）
# ══════════════════════════════════════════════════════════════════════════════

def vertical_bar_chart(
    data: list[float],
    labels: list[str],
    title: str,
    unit: str = "",
    color: str = GREEN,
    output_path: Path | None = None,
) -> Path:
    """
    長條圖動畫（6s / 180 frames）

    時段分佈：
      0 – 30  : 背景 + X/Y 軸漸入
      30 – 120: 長條從底部依序長出（每根間隔 0.2s / 6 frames）
      120 –160: 所有數字從 0 跳動到最終值
      160 –180: 趨勢線從左到右畫出
    """
    if output_path is None:
        output_path = CHARTS_DIR / "chart_vertical_bar.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n       = len(data)
    y_max   = max(data) * 1.3
    TOTAL   = 6 * FPS          # 180
    STAGGER = 6                 # 0.2s per bar
    BAR_DUR = max(15, (90 - (n - 1) * STAGGER))  # frames each bar takes to grow

    fig, ax = _base_fig()
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(0, y_max)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, fontproperties=FONT_PROP, color=DIMWHITE, fontsize=14)
    ax.tick_params(colors=DIMWHITE, length=0)
    ax.set_yticks([])

    ax.set_title(title, fontsize=34, fontweight="bold", color=WHITE,
                 pad=24, fontproperties=FONT_PROP)
    if unit:
        ax.set_ylabel(unit, fontsize=15, color=DIMWHITE, labelpad=10,
                      fontproperties=FONT_PROP)

    # 水平格線（靜態，背景）
    for gv in np.linspace(0, y_max * 0.8, 5):
        ax.axhline(gv, color=DIMWHITE, linewidth=0.4, alpha=0.25)

    # 動態 X 軸線（Phase 1 漸入）
    x_axis, = ax.plot([], [], color=DIMWHITE, linewidth=1.5, alpha=0.7)

    # 長條（初始高度為 0）
    bars = ax.bar(range(n), [0.0] * n, color=color, alpha=0.85,
                  width=0.55, edgecolor=BG, linewidth=1.0)

    # 數值標籤
    val_txts = [
        ax.text(i, 0, "", ha="center", va="bottom", color=WHITE,
                fontsize=14, fontweight="bold", fontproperties=FONT_PROP)
        for i in range(n)
    ]

    # 趨勢線 + 點
    trend_line, = ax.plot([], [], color=YELLOW, linewidth=2.5,
                          linestyle="--", alpha=0.85, zorder=5)
    trend_dots, = ax.plot([], [], "o", color=YELLOW, markersize=7, zorder=6)

    def update(frame: int) -> None:
        # Phase 1：X 軸從左向右畫出
        if frame < 30:
            p  = frame / 30.0
            x_axis.set_data([-0.5, -0.5 + p * (n + 0.5)], [0, 0])
        else:
            x_axis.set_data([-0.5, n - 0.5], [0, 0])

        # Phase 2：長條長出
        for i, (bar, val) in enumerate(zip(bars, data)):
            t0 = 30 + i * STAGGER
            t1 = t0 + BAR_DUR
            if frame < t0:
                h = 0.0
            elif frame >= t1:
                h = val
            else:
                h = val * _ease_out((frame - t0) / BAR_DUR)
            bar.set_height(max(h, 0.0))

        # Phase 3：數字跳動（120–160 frames，所有數字同步）
        for i, (txt, val) in enumerate(zip(val_txts, data)):
            bar_done = 30 + i * STAGGER + BAR_DUR
            if frame < max(bar_done, 120):
                txt.set_text("")
            else:
                p = _ease_out(min((frame - 120) / 40.0, 1.0))
                txt.set_text(_fmt(val * p))
                txt.set_position((i, bars[i].get_height() + y_max * 0.015))

        # Phase 4：趨勢線從左到右（160–180 frames）
        if frame >= 160:
            p     = min((frame - 160) / 20.0, 1.0)
            n_seg = p * (n - 1)
            nf    = int(n_seg)
            frac  = n_seg - nf
            xs = list(range(nf + 1))
            ys = list(data[:nf + 1])
            if frac > 0 and nf < n - 1:
                xs.append(nf + frac)
                ys.append(data[nf] + frac * (data[nf + 1] - data[nf]))
            trend_line.set_data(xs, ys)
            trend_dots.set_data(list(range(nf + 1)), data[:nf + 1])
        else:
            trend_line.set_data([], [])
            trend_dots.set_data([], [])

    anim = animation.FuncAnimation(fig, update, frames=TOTAL,
                                   interval=1000 / FPS)
    anim.save(str(output_path), writer=_writer())
    plt.close(fig)
    print(f"  [chart] vertical_bar → {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# 圖表二：Horizontal Bar Chart（橫向長條圖，5秒）
# ══════════════════════════════════════════════════════════════════════════════

def horizontal_bar_chart(
    data: list[float],
    labels: list[str],
    title: str,
    highlight_index: int | None = None,
    unit: str = "%",
    output_path: Path | None = None,
) -> Path:
    """
    橫向長條圖動畫（5s / 150 frames）

    時段分佈：
      0  – 20 : 背景
      20 – 110: 橫條從左邊依序延伸（每條間隔 0.3s / 9 frames）
      110– 130: 數值從左端出現
      130– 150: 標註框從右邊飛入
    """
    if output_path is None:
        output_path = CHARTS_DIR / "chart_horizontal_bar.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n       = len(data)
    x_max   = max(data) * 1.35
    TOTAL   = 5 * FPS          # 150
    STAGGER = 9                 # 0.3s per bar
    BAR_DUR = max(15, (90 - (n - 1) * STAGGER))

    hi = highlight_index if highlight_index is not None else int(np.argmax(data))

    fig, ax = _base_fig()
    ax.set_xlim(0, x_max)
    ax.set_ylim(-0.55, n - 0.45)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontproperties=FONT_PROP, color=DIMWHITE, fontsize=16)
    ax.tick_params(colors=DIMWHITE, length=0)
    ax.set_xticks([])

    ax.set_title(title, fontsize=34, fontweight="bold", color=WHITE,
                 pad=24, fontproperties=FONT_PROP)

    # 顏色：highlight → YELLOW，最大值 → GREEN，其餘 → 深綠
    bar_colors = [
        YELLOW if i == hi else (GREEN if data[i] == max(data) else "#2a5a3a")
        for i in range(n)
    ]

    # 橫條（初始寬度為 0）
    bars = ax.barh(range(n), [0.0] * n, color=bar_colors,
                   edgecolor=BG, linewidth=1.0, height=0.55)

    # 數值標籤
    val_txts = [
        ax.text(0, i, "", ha="left", va="center", color=WHITE,
                fontsize=14, fontweight="bold", fontproperties=FONT_PROP)
        for i in range(n)
    ]

    # 標註框（起始位置在畫面右側外）
    _anno_x0 = x_max * 1.6
    _anno_x1 = data[hi] + x_max * 0.03
    anno = ax.text(
        _anno_x0, hi,
        f"★  {_fmt(data[hi])}{unit}",
        ha="left", va="center", color=YELLOW,
        fontsize=15, fontweight="bold", fontproperties=FONT_PROP,
        bbox=dict(facecolor="#1a2a1a", edgecolor=YELLOW,
                  boxstyle="round,pad=0.45", linewidth=2.0),
    )

    def update(frame: int) -> None:
        # Phase 2：橫條延伸
        for i, (bar, val) in enumerate(zip(bars, data)):
            t0 = 20 + i * STAGGER
            t1 = t0 + BAR_DUR
            if frame < t0:
                w = 0.0
            elif frame >= t1:
                w = val
            else:
                w = val * _ease_out((frame - t0) / BAR_DUR)
            bar.set_width(max(w, 0.0))

        # Phase 3：數值出現（110–130）
        for i, (txt, val) in enumerate(zip(val_txts, data)):
            if frame < 110:
                txt.set_text("")
            else:
                p = _ease_out(min((frame - 110) / 20.0, 1.0))
                txt.set_text(f"{_fmt(val * p)}{unit}")
                txt.set_position((bars[i].get_width() + x_max * 0.01, i))

        # Phase 4：標註框飛入（130–150）
        if frame >= 130:
            p = _ease_in_out(min((frame - 130) / 20.0, 1.0))
            anno.set_position((_anno_x0 + (_anno_x1 - _anno_x0) * p, hi))

    anim = animation.FuncAnimation(fig, update, frames=TOTAL,
                                   interval=1000 / FPS)
    anim.save(str(output_path), writer=_writer())
    plt.close(fig)
    print(f"  [chart] horizontal_bar → {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# 圖表三：Diverging Bar Chart（正負長條圖，7秒）
# ══════════════════════════════════════════════════════════════════════════════

def diverging_bar_chart(
    data: list[float],
    labels: list[str],
    title: str,
    unit: str = "%",
    output_path: Path | None = None,
) -> Path:
    """
    正負長條圖動畫（7s / 210 frames）

    時段分佈：
      0  – 30 : 零軸線從左往右畫出
      30 – 90 : 負值紅色長條從零往下長（依序）
      90 – 150: 正值綠色長條從零往上長（依序）
      150– 180: 首個正值標註點出現
      180– 210: 標註點閃爍 3 次
    """
    if output_path is None:
        output_path = CHARTS_DIR / "chart_diverging_bar.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n        = len(data)
    abs_max  = max(abs(min(data, default=0)), abs(max(data, default=1)), 1.0)
    y_range  = abs_max * 1.4
    TOTAL    = 7 * FPS    # 210

    neg_idx = [i for i, v in enumerate(data) if v < 0]
    pos_idx = [i for i, v in enumerate(data) if v >= 0]

    # 找第一個轉正點
    turn_idx = next(
        (i for i in range(1, n) if data[i - 1] < 0 and data[i] >= 0),
        pos_idx[0] if pos_idx else None,
    )

    # 各組動畫持續時間
    NEG_STAGGER = max(4, 50 // max(len(neg_idx), 1))
    NEG_DUR     = max(15, 60 - (len(neg_idx) - 1) * NEG_STAGGER)
    POS_STAGGER = max(4, 50 // max(len(pos_idx), 1))
    POS_DUR     = max(15, 60 - (len(pos_idx) - 1) * POS_STAGGER)

    fig, ax = _base_fig()
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(-y_range, y_range)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, fontproperties=FONT_PROP, color=DIMWHITE, fontsize=14)
    ax.tick_params(colors=DIMWHITE, length=0)
    ax.set_yticks([])

    ax.set_title(title, fontsize=34, fontweight="bold", color=WHITE,
                 pad=24, fontproperties=FONT_PROP)

    # 動態零軸線（Phase 1）
    zero_line, = ax.plot([], [], color=DIMWHITE, linewidth=2.0, alpha=0.8, zorder=3)

    # 長條（初始 y=0, height=0）
    bar_colors = [RED if v < 0 else GREEN for v in data]
    bars = ax.bar(range(n), [0.0] * n, bottom=0.0,
                  color=bar_colors, alpha=0.85,
                  width=0.55, edgecolor=BG, linewidth=1.0)

    # 數值標籤
    val_txts = [
        ax.text(i, 0, "", ha="center",
                va="top" if v < 0 else "bottom",
                color=WHITE, fontsize=13, fontweight="bold",
                fontproperties=FONT_PROP)
        for i, v in enumerate(data)
    ]

    # 轉折點標註
    anno = None
    if turn_idx is not None:
        anno = ax.text(
            turn_idx, data[turn_idx] + y_range * 0.1,
            f"↑ 轉正",
            ha="center", va="bottom",
            color=YELLOW, fontsize=15, fontweight="bold",
            fontproperties=FONT_PROP,
            bbox=dict(facecolor="#1a2a1a", edgecolor=YELLOW,
                      boxstyle="round,pad=0.4", linewidth=2.0),
            visible=False, zorder=10,
        )
        # 箭頭線
        anno_line, = ax.plot(
            [turn_idx, turn_idx],
            [0, data[turn_idx] + y_range * 0.08],
            color=YELLOW, linewidth=1.8, linestyle="--",
            alpha=0.0, zorder=9,
        )
    else:
        anno_line = None

    def _set_bar(i: int, val: float, frac: float) -> None:
        """以 frac (0→1) 設定第 i 根長條的動畫高度"""
        h_anim = abs(val) * frac
        if val < 0:
            bars[i].set_y(-h_anim)
            bars[i].set_height(h_anim)
        else:
            bars[i].set_y(0.0)
            bars[i].set_height(h_anim)

    def update(frame: int) -> None:
        # Phase 1：零軸線漸入（0–30）
        if frame < 30:
            p = frame / 30.0
            zero_line.set_data([-0.5, -0.5 + p * n], [0, 0])
        else:
            zero_line.set_data([-0.5, n - 0.5], [0, 0])

        # Phase 2：負值長條（30–90）
        for j, i in enumerate(neg_idx):
            t0 = 30 + j * NEG_STAGGER
            t1 = t0 + NEG_DUR
            if frame < t0:
                frac = 0.0
            elif frame >= t1:
                frac = 1.0
            else:
                frac = _ease_out((frame - t0) / NEG_DUR)
            _set_bar(i, data[i], frac)

        # Phase 3：正值長條（90–150）
        for j, i in enumerate(pos_idx):
            t0 = 90 + j * POS_STAGGER
            t1 = t0 + POS_DUR
            if frame < t0:
                frac = 0.0
            elif frame >= t1:
                frac = 1.0
            else:
                frac = _ease_out((frame - t0) / POS_DUR)
            _set_bar(i, data[i], frac)

        # 數值標籤（長條完成後出現）
        for j, (txt, val) in enumerate(zip(val_txts, data)):
            if val < 0:
                done = 30 + neg_idx.index(j) * NEG_STAGGER + NEG_DUR if j in neg_idx else 90
            else:
                done = 90 + pos_idx.index(j) * POS_STAGGER + POS_DUR if j in pos_idx else 150
            if frame >= done:
                sign = "+" if val >= 0 else ""
                txt.set_text(f"{sign}{_fmt(val)}{unit}")
                offset = y_range * 0.05
                txt.set_position((j, val - offset if val < 0 else val + offset * 0.4))
            else:
                txt.set_text("")

        # Phase 4：標註出現（150–180）
        if anno and frame >= 150:
            anno.set_visible(True)
            if anno_line:
                anno_line.set_alpha(min((frame - 150) / 30.0, 1.0))

        # Phase 5：標註閃爍（180–210，3 次）
        if anno and frame >= 180:
            cycle = (frame - 180) % 20
            anno.set_visible(cycle < 10)

    anim = animation.FuncAnimation(fig, update, frames=TOTAL,
                                   interval=1000 / FPS)
    anim.save(str(output_path), writer=_writer())
    plt.close(fig)
    print(f"  [chart] diverging_bar → {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════════════════════
# 相容介面：generate_chart(chart_id, config)
# ══════════════════════════════════════════════════════════════════════════════

def generate_chart(chart_id: int, config: dict) -> Path:
    """
    main_confirm.py 呼叫介面。

    路由規則：
      1 → vertical_bar_chart  （EPS 或營收趨勢）
      2 → horizontal_bar_chart（業務/同業比較）
      3 → diverging_bar_chart  （YoY 成長率正負圖）

    config["chart_data"] 結構：
      {
        "quarters": [...],    # X 軸標籤
        "eps": [...],         # 圖1 優先
        "revenue": [...],     # 圖1 備用
        "segments": {...},    # 圖2 {名稱: 數值}
        "yoy_growth": [...],  # 圖3
        "unit": "億",
        "currency": "NTD",
      }
    """
    note = config.get(f"chart{chart_id}_note", "")
    if note:
        print(f"[圖表{chart_id}] 套用修改意見：{note}")

    cd     = config.get("chart_data") or {}
    qtrs   = cd.get("quarters") or ["Q1", "Q2", "Q3", "Q4"]
    unit   = cd.get("currency", "") + " " + cd.get("unit", "")

    if chart_id == 1:
        data  = cd.get("eps") or cd.get("revenue") or [1.0, 1.2, 1.5, 1.8]
        title = config.get("title", "財務趨勢") + " — EPS"
        return vertical_bar_chart(
            data=data,
            labels=qtrs[-len(data):] if len(qtrs) >= len(data) else qtrs,
            title=title,
            unit=unit.strip() or "NT$",
            output_path=CHARTS_DIR / "chart1_vertical_bar.mp4",
        )

    if chart_id == 2:
        segs = cd.get("segments") or {"HPC": 52, "Smartphone": 33, "IoT": 15}
        data   = list(segs.values())
        labels = list(segs.keys())
        hi = int(np.argmax(data))
        return horizontal_bar_chart(
            data=data,
            labels=labels,
            title=config.get("title", "業務佔比") + " — 收入結構",
            highlight_index=hi,
            unit="%",
            output_path=CHARTS_DIR / "chart2_horizontal_bar.mp4",
        )

    # chart_id == 3
    yoy  = cd.get("yoy_growth") or [-5.0, -2.0, 1.5, 4.0, 6.5, 9.0, 12.0, 15.0]
    return diverging_bar_chart(
        data=yoy,
        labels=qtrs[-len(yoy):] if len(qtrs) >= len(yoy) else qtrs,
        title=config.get("title", "營收年增率"),
        unit="%",
        output_path=CHARTS_DIR / "chart3_diverging_bar.mp4",
    )
