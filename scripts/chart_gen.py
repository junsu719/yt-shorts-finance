import os
import re
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as _manim
from matplotlib import font_manager as _fm

# Register Noto Sans CJK so Chinese/Traditional text renders correctly
_CJK_FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]
for _p in _CJK_FONT_PATHS:
    if os.path.exists(_p):
        _fm.fontManager.addfont(_p)
        matplotlib.rcParams["font.family"] = "Noto Sans CJK JP"
        break

_BG    = "#0d1117"
_GREEN = "#3fb950"
_RED   = "#f85149"
_BLUE  = "#58a6ff"
_GRAY  = "#8b949e"
_TEXT  = "#e6edf3"
_GRID  = "#21262d"

_FIG_W, _FIG_H = 6, 10.67
_DPI = 180


def _setup_fig():
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H), dpi=_DPI)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.tick_params(colors=_GRAY, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(_GRID)
    ax.grid(axis="y", color=_GRID, linewidth=0.8, linestyle="--", alpha=0.7)
    return fig, ax


def _watermark(fig):
    fig.text(0.5, 0.015, "數據來源：公開財報", ha="center", fontsize=8, color=_GRAY, alpha=0.5)


def _save(fig, path):
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(path, dpi=_DPI, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)


# ── Chart implementations ─────────────────────────────────────────────────────

def _revenue_bar(data: dict, output_path: str):
    fig, ax = _setup_fig()
    quarters = data["quarters"]
    revenue  = data["revenue"]
    yoy      = data.get("yoy_growth", [0] * len(quarters))

    bar_colors = [_GREEN if y >= 0 else _RED for y in yoy]
    bars = ax.bar(quarters, revenue, color=bar_colors, width=0.5, zorder=3)

    rev_range = max(revenue) - min(revenue) or max(revenue)
    for bar, val, y in zip(bars, revenue, yoy):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + rev_range * 0.02,
                f"{val:,}", ha="center", va="bottom",
                color=_TEXT, fontsize=10, fontweight="bold")
        sign = "+" if y >= 0 else ""
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() * 0.5,
                f"{sign}{y:.1f}%", ha="center", va="center",
                color=_BG, fontsize=9, fontweight="bold")

    ax2 = ax.twinx()
    ax2.plot(quarters, yoy, color=_BLUE, marker="o",
             linewidth=2, markersize=6, zorder=4)
    ax2.set_facecolor(_BG)
    ax2.tick_params(colors=_GRAY, labelsize=9)
    for spine in ax2.spines.values():
        spine.set_color(_GRID)
    ax2.set_ylabel("YoY %", color=_GRAY, fontsize=9)

    unit = data.get("unit", "億")
    currency = data.get("currency", "NTD")
    ax.set_title(f"{data.get('company', '')} 季營收（{currency} {unit}）",
                 color=_TEXT, fontsize=13, fontweight="bold", pad=16)
    ax.set_ylabel(f"營收（{unit}）", color=_GRAY, fontsize=9)
    _watermark(fig)
    _save(fig, output_path)


def _gross_margin(data: dict, output_path: str):
    fig, ax = _setup_fig()
    quarters = data["quarters"]
    gm       = data["gross_margin"]
    x        = range(len(quarters))

    ax.fill_between(x, gm, min(gm) - 3, alpha=0.18, color=_GREEN)
    ax.plot(x, gm, color=_GREEN, marker="o", linewidth=2.5, markersize=8, zorder=3)

    gm_range = max(gm) - min(gm) or 2
    for i, val in enumerate(gm):
        ax.text(i, val + gm_range * 0.12, f"{val:.1f}%",
                ha="center", va="bottom", color=_TEXT, fontsize=11, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(quarters)
    ax.set_ylim(min(gm) - 6, max(gm) + 6)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title(f"{data.get('company', '')} 毛利率趨勢",
                 color=_TEXT, fontsize=13, fontweight="bold", pad=16)
    _watermark(fig)
    _save(fig, output_path)


def _eps_trend(data: dict, output_path: str):
    fig, ax = _setup_fig()
    quarters = data["quarters"]
    eps      = data["eps"]

    bar_colors = []
    for i, val in enumerate(eps):
        bar_colors.append(_GREEN if i == 0 or val >= eps[i - 1] else _RED)

    ax.bar(quarters, eps, color=bar_colors, width=0.5, alpha=0.65, zorder=2)
    ax.plot(quarters, eps, color=_BLUE, marker="D",
            linewidth=2, markersize=7, zorder=3)

    eps_range = max(eps) - min(eps) or max(eps)
    for i, val in enumerate(eps):
        ax.text(i, val + eps_range * 0.05, f"{val}",
                ha="center", va="bottom", color=_TEXT, fontsize=12, fontweight="bold")

    currency = data.get("currency", "NTD")
    ax.set_title(f"{data.get('company', '')} EPS（{currency}）",
                 color=_TEXT, fontsize=13, fontweight="bold", pad=16)
    ax.set_ylabel("EPS", color=_GRAY, fontsize=9)
    _watermark(fig)
    _save(fig, output_path)


def _candlestick(data: dict, output_path: str):
    """Synthetic candlestick: open/close derived from revenue trend."""
    fig, ax = _setup_fig()
    quarters  = data["quarters"]
    revenue   = data["revenue"]
    net       = data.get("net_profit", [r * 0.2 for r in revenue])

    for i, (rev, np_val) in enumerate(zip(revenue, net)):
        ratio     = (np_val / rev) if rev else 0.15
        body_lo   = rev * (1 - ratio * 0.4)
        body_hi   = rev * (1 + ratio * 0.25)
        wick_lo   = body_lo * 0.93
        wick_hi   = body_hi * 1.04

        is_up  = (i == 0) or (rev >= revenue[i - 1])
        color  = _GREEN if is_up else _RED

        ax.plot([i, i], [wick_lo, wick_hi], color=color, linewidth=1.5, zorder=2)
        rect = mpatches.Rectangle(
            (i - 0.2, min(body_lo, body_hi)), 0.4, abs(body_hi - body_lo),
            facecolor=color, edgecolor=color, zorder=3
        )
        ax.add_patch(rect)
        ax.text(i, wick_hi + (wick_hi - wick_lo) * 0.06, f"{rev:,}",
                ha="center", va="bottom", color=_TEXT, fontsize=9, fontweight="bold")

    ax.set_xticks(range(len(quarters)))
    ax.set_xticklabels(quarters)
    unit     = data.get("unit", "億")
    currency = data.get("currency", "NTD")
    ax.set_title(f"{data.get('company', '')} 財務K線（{currency} {unit}）",
                 color=_TEXT, fontsize=13, fontweight="bold", pad=16)
    _watermark(fig)
    _save(fig, output_path)


def _segment_bar(data: dict, output_path: str):
    fig, ax = _setup_fig()
    segments = data.get("segments", {"HPC": 52, "Smartphone": 33, "IoT": 7, "Auto": 5, "Others": 3})
    labels   = list(segments.keys())
    values   = list(segments.values())

    palette = [_GREEN, _BLUE, "#f0883e", "#bc8cff", _GRAY, _RED]
    colors  = [palette[i % len(palette)] for i in range(len(labels))]

    bars = ax.barh(labels, values, color=colors, height=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
                f"{val}%", va="center", color=_TEXT, fontsize=12, fontweight="bold")

    ax.set_xlim(0, max(values) * 1.25)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title(f"{data.get('company', '')} 業務收入占比",
                 color=_TEXT, fontsize=13, fontweight="bold", pad=16)
    ax.invert_yaxis()
    ax.grid(axis="x", color=_GRID, linewidth=0.8, linestyle="--", alpha=0.7)
    ax.grid(axis="y", visible=False)
    _watermark(fig)
    _save(fig, output_path)


# ── Education charts (non-farm payroll / macro education videos) ──────────────

def _nonfarm_comparison_bar(data: dict, output_path: str):
    """Chart 1: Expected vs Actual non-farm payroll bar chart."""
    fig, ax = _setup_fig()

    expected = data.get("expected", 8.5)
    actual   = data.get("actual", 17.2)
    period   = data.get("period", "2026年5月")

    categories = ["市場預期", "實際數據"]
    values     = [expected, actual]
    colors     = ["#f0883e", _GREEN]

    bars = ax.bar(categories, values, color=colors, width=0.45, zorder=3)

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.4,
            f"{val}萬人",
            ha="center", va="bottom",
            color=_TEXT, fontsize=16, fontweight="bold",
        )

    # Double-arrow between the two bars
    mid_x = 0.5
    ax.annotate(
        "", xy=(mid_x + 0.42, actual), xytext=(mid_x + 0.42, expected),
        arrowprops=dict(arrowstyle="<->", color=_BLUE, lw=2.5),
    )
    ax.text(
        mid_x + 0.62, (expected + actual) / 2,
        "×2.0倍", color=_BLUE, fontsize=14, fontweight="bold", va="center",
    )

    ax.set_ylim(0, actual * 1.45)
    ax.set_ylabel("新增就業人數（萬人）", color=_GRAY, fontsize=10)
    ax.set_title(
        f"{period} 非農就業報告\n實際幾乎是預期兩倍",
        color=_TEXT, fontsize=13, fontweight="bold", pad=16,
    )
    fig.text(0.5, 0.015, "數字僅供教學示範", ha="center", fontsize=8, color=_GRAY, alpha=0.5)
    _save(fig, output_path)


def _good_news_bad_news_flow(data: dict, output_path: str):
    """Chart 2: Logic flow — good news becomes bad news for markets."""
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H), dpi=_DPI)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11)
    ax.axis("off")

    nodes = [
        (5, 10.0, "就業市場強勁", "#3fb950", "✅ 好消息"),
        (5,  8.4, "經濟不需要刺激", "#f0883e", ""),
        (5,  6.8, "聯準會不降息", "#f0883e", ""),
        (5,  5.2, "利率維持高位", "#f85149", ""),
        (5,  3.6, "成長股估值壓縮", "#f85149", ""),
        (5,  2.0, "台股跟進暴跌", "#f85149", "❌ 壞結果"),
    ]

    bw, bh = 6.0, 0.75
    for x, y, text, color, badge in nodes:
        fancy = mpatches.FancyBboxPatch(
            (x - bw / 2, y - bh / 2), bw, bh,
            boxstyle="round,pad=0.15",
            facecolor=color, edgecolor=color, alpha=0.25, zorder=2,
        )
        ax.add_patch(fancy)
        ax.text(x, y, text, ha="center", va="center",
                color=_TEXT, fontsize=12, fontweight="bold", zorder=3)
        if badge:
            ax.text(x + bw / 2 - 0.1, y, badge, ha="right", va="center",
                    color=_TEXT, fontsize=9, zorder=3)

    for i in range(len(nodes) - 1):
        _, y1, _, _, _ = nodes[i]
        _, y2, _, _, _ = nodes[i + 1]
        ax.annotate(
            "", xy=(5, y2 + bh / 2 + 0.08), xytext=(5, y1 - bh / 2 - 0.08),
            arrowprops=dict(arrowstyle="-|>", color=_GRAY, lw=2, mutation_scale=20),
            zorder=3,
        )

    ax.text(5, 10.8, "好消息為什麼變壞消息？", ha="center", va="center",
            color=_TEXT, fontsize=14, fontweight="bold")
    fig.text(0.5, 0.015, "邏輯示意圖，非投資建議", ha="center", fontsize=8, color=_GRAY, alpha=0.5)
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(output_path, dpi=_DPI, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)


def _taiwan_stock_decline(data: dict, output_path: str):
    """Chart 3: Taiwan stock index intraday decline concept chart (~-2700pts)."""
    fig, ax = _setup_fig()

    np.random.seed(99)
    n = 30
    # Intraday prices: open ~22000, gradual drift, sharp drop at end
    prices = np.zeros(n)
    prices[0] = 22050
    for i in range(1, n):
        if i < 20:
            prices[i] = prices[i - 1] + np.random.normal(-5, 25)
        elif i < 26:
            prices[i] = prices[i - 1] + np.random.normal(-60, 40)
        else:
            prices[i] = prices[i - 1] + np.random.normal(-160, 30)

    # Force final value to ~19300 (drop of ~2700)
    target_close = 19310
    prices[-1] = target_close
    prices[-2] = target_close + np.random.uniform(100, 250)

    x = np.arange(n)
    ax.fill_between(x, prices, min(prices) - 150, alpha=0.15, color=_RED)
    ax.plot(x, prices, color=_RED, linewidth=2.5, zorder=3)

    # Mark non-farm report moment
    event_x = 22
    ax.axvline(event_x, color="#f0883e", linewidth=1.5, linestyle="--", alpha=0.8)
    ax.text(event_x + 0.4, prices[event_x] + 200, "非農報告\n公布時刻",
            color="#f0883e", fontsize=9, fontweight="bold", linespacing=1.4)

    # Annotate drop
    ax.annotate(
        f"↓ 2,700點\n({target_close:,})",
        xy=(n - 1, target_close),
        xytext=(n - 9, target_close - 600),
        color=_RED, fontsize=10, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=_RED, lw=1.5),
    )
    ax.text(0.5, prices[0] + 180, f"開盤 {prices[0]:,.0f}", color=_TEXT,
            fontsize=10, fontweight="bold")

    tick_pos = [0, 6, 12, 18, 24, n - 1]
    tick_lab = ["09:00", "10:00", "11:00", "12:00", "13:00", "13:30"]
    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_lab, fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_ylabel("指數（點）", color=_GRAY, fontsize=9)
    ax.set_title("台股加權指數今日走勢示意圖",
                 color=_TEXT, fontsize=13, fontweight="bold", pad=16)
    fig.text(0.5, 0.015, "示意圖，非實際數據", ha="center", fontsize=8, color=_GRAY, alpha=0.5)
    _save(fig, output_path)


_EDUCATION_CHART_FUNCS = [
    _nonfarm_comparison_bar,
    _good_news_bad_news_flow,
    _taiwan_stock_decline,
]


def generate_education_chart(chart_data: dict, chart_idx: int, output_path: str):
    """Dispatch to education-specific chart. chart_idx 0/1/2 → comparison/flow/decline."""
    nonfarm_data = chart_data.get("nonfarm", {})
    func = _EDUCATION_CHART_FUNCS[chart_idx % len(_EDUCATION_CHART_FUNCS)]
    func(nonfarm_data, output_path)


# ── Market / macro chart (fallback when chart_data is null) ──────────────────

def _extract_index_changes(narration: str) -> tuple[dict[str, float], bool]:
    """Parse % changes for major indices from narration. Returns (changes, is_demo)."""
    changes: dict[str, float] = {}

    index_map = [
        ("道瓊",     ["道瓊", "Dow"]),
        ("標普500",  ["標普", "S&P", "S＆P"]),
        ("納斯達克", ["納斯達克", "Nasdaq", "NASDAQ"]),
        ("台股加權", ["台股", "加權指數", "TAIEX", "大盤"]),
    ]

    decline_words = {"跌", "下跌", "重挫", "大跌", "暴跌", "fell", "drop", "loss", "lost", "decline", "-"}

    for label, keywords in index_map:
        for kw in keywords:
            m = re.search(rf'{re.escape(kw)}.{{0,60}}?([\d.]+)\s*[%％]', narration)
            if m:
                pct = float(m.group(1))
                context = narration[m.start(): m.start(1)]
                if any(w in context for w in decline_words):
                    pct = -pct
                changes[label] = pct
                break

    if changes:
        return changes, False
    return {"道瓊": -3.5, "標普500": -4.2, "納斯達克": -5.8}, True


def _market_index_bar(changes: dict[str, float], is_demo: bool, output_path: str):
    fig, ax = _setup_fig()
    labels = list(changes.keys())
    values = list(changes.values())
    colors = [_GREEN if v >= 0 else _RED for v in values]

    y_pos = range(len(labels))
    bars = ax.barh(y_pos, values, color=colors, height=0.45, zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=11)

    x_max = max(abs(v) for v in values) * 1.65
    ax.set_xlim(-x_max if any(v < 0 for v in values) else 0, x_max)

    for bar, val in zip(bars, values):
        sign = "+" if val >= 0 else ""
        offset = x_max * 0.04
        x_pos = val + (offset if val >= 0 else -offset)
        ha = "left" if val >= 0 else "right"
        ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                f"{sign}{val:.1f}%", va="center", ha=ha,
                color=_TEXT, fontsize=13, fontweight="bold")

    ax.axvline(0, color=_GRAY, linewidth=1, alpha=0.7, zorder=2)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax.invert_yaxis()
    ax.grid(axis="x", color=_GRID, linewidth=0.8, linestyle="--", alpha=0.7)
    ax.grid(axis="y", visible=False)

    title = "大盤指數單日表現" + ("（示意圖）" if is_demo else "")
    ax.set_title(title, color=_TEXT, fontsize=14, fontweight="bold", pad=20)
    watermark = "示意圖，數據僅供參考" if is_demo else "數據來源：市場公開資訊"
    fig.text(0.5, 0.015, watermark, ha="center", fontsize=8, color=_GRAY, alpha=0.5)
    _save(fig, output_path)


def _tsmc_price_chart(output_path: str):
    """台積電 (2330) 近一個月股價走勢示意圖 for AI / supply-chain market analysis videos."""
    import datetime

    # 22 trading days: ~May 4 – Jun 2, 2026 (示意用，非真實行情)
    np.random.seed(7)
    days = 22
    base_prices = np.array([
        905, 912, 908, 920, 928,   # week 1
        922, 930, 938, 942, 935,   # week 2
        940, 948, 955, 960, 952,   # week 3
        958, 963, 970, 968, 975,   # week 4
        978, 982,                   # week 5 partial
    ], dtype=float)

    # Slight random noise for realism
    prices = base_prices + np.random.normal(0, 3, days)

    # Trading-day labels Mon–Fri
    start = datetime.date(2026, 5, 4)
    dates: list[datetime.date] = []
    d = start
    while len(dates) < days:
        if d.weekday() < 5:
            dates.append(d)
        d += datetime.timedelta(days=1)

    # GTC Taipei = Jun 1 → index 21 (last day before Jun 2)
    event_idx = 20

    fig, ax = _setup_fig()
    x = np.arange(days)

    ax.fill_between(x, prices, prices.min() - 25, alpha=0.12, color=_GREEN)
    ax.plot(x, prices, color=_GREEN, linewidth=2.5, zorder=3)
    ax.scatter([event_idx], [prices[event_idx]], color=_RED, s=80, zorder=5)

    ax.axvline(event_idx, color=_RED, linewidth=1.2, linestyle="--", alpha=0.7, zorder=2)
    ax.text(event_idx + 0.35, prices.max() - 5,
            "GTC\nTaipei\n6/1", color=_RED, fontsize=8, va="top", linespacing=1.4)

    # Latest price label
    ax.text(days - 1, prices[-1] + 6, f"NT${prices[-1]:.0f}",
            color=_TEXT, fontsize=11, fontweight="bold", ha="right")

    # X-axis: every 4 days
    ticks = list(range(0, days, 4)) + [days - 1]
    ax.set_xticks(ticks)
    ax.set_xticklabels([dates[i].strftime("%m/%d") for i in ticks], fontsize=9)

    ax.set_ylabel("股價 (TWD)", color=_GRAY, fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}"))

    pct = (prices[-1] - prices[0]) / prices[0] * 100
    sign = "+" if pct >= 0 else ""
    ax.text(0.97, 0.04, f"月漲幅 {sign}{pct:.1f}%",
            transform=ax.transAxes, ha="right", va="bottom",
            color=_GREEN if pct >= 0 else _RED, fontsize=12, fontweight="bold")

    ax.set_title("台積電 (2330) 近一個月走勢",
                 color=_TEXT, fontsize=13, fontweight="bold", pad=16)
    fig.text(0.5, 0.015, "示意圖，數據僅供參考",
             ha="center", fontsize=8, color=_GRAY, alpha=0.5)
    _save(fig, output_path)


def generate_market_chart(narration: str, output_path: str):
    """Market chart. Uses TSMC price trend when narration covers 台積電/台股 topics,
    otherwise generates an index-change bar chart. Always succeeds."""
    try:
        if "台積電" in narration or "台股" in narration:
            _tsmc_price_chart(output_path)
        else:
            changes, is_demo = _extract_index_changes(narration)
            _market_index_bar(changes, is_demo, output_path)
    except Exception:
        _market_index_bar({"道瓊": -3.5, "標普500": -4.2, "納斯達克": -5.8}, True, output_path)


# ── Public API ────────────────────────────────────────────────────────────────

_CHART_FUNCS = {
    "revenue_bar":  _revenue_bar,
    "gross_margin": _gross_margin,
    "eps_trend":    _eps_trend,
    "candlestick":  _candlestick,
    "segment_bar":  _segment_bar,
}

CHART_TYPES = list(_CHART_FUNCS)


def generate_finance_chart(chart_data: dict, chart_type: str, output_path: str):
    func = _CHART_FUNCS.get(chart_type)
    if func is None:
        raise ValueError(f"Unknown chart_type '{chart_type}'. Must be one of {CHART_TYPES}")
    func(chart_data, output_path)


def chart_to_clip(chart_path: str, output_path: str, duration: float = 5):
    """Convert a PNG chart to a 9:16 MP4 with a subtle Ken Burns zoom."""
    total_frames = int(round(duration * 30))
    subprocess.run(
        [
            "ffmpeg", "-y", "-loop", "1", "-i", chart_path,
            "-t", str(duration),
            "-vf", (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                f"zoompan=z='min(zoom+0.0008,1.05)'"
                f":x='iw/2-(iw/zoom/2)'"
                f":y='ih/2-(ih/zoom/2)'"
                f":d={total_frames}:s=1080x1920:fps=30"
            ),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-an",
            output_path,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Animated chart API — portrait 1080×1920 MP4 for Shorts pipeline
# ══════════════════════════════════════════════════════════════════════════════

def _anim_writer():
    return _manim.FFMpegWriter(fps=30, codec="libx264",
                                extra_args=["-pix_fmt", "yuv420p"])


def _anim_ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _anim_ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _anim_fmt(val: float) -> str:
    if abs(val) >= 1000:
        return f"{val:,.0f}"
    if abs(val) >= 10:
        return f"{val:.1f}"
    return f"{val:.2f}"


def _portrait_fig():
    """1080×1920 portrait figure — matches chart_gen.py's static chart dimensions."""
    fig, ax = plt.subplots(figsize=(6, 10.67), dpi=180)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    for sp in ax.spines.values():
        sp.set_visible(False)
    return fig, ax


# ── Animated Vertical Bar (6 s / 180 frames) ─────────────────────────────────

def _anim_vertical_bar(
    data: list, labels: list, title: str, unit: str,
    color: str, output_path: str, duration: float = 6,
    bar_colors: list | None = None,
    watermark_text: str = "",
    annotation_idx: int = -1,
    annotation_text: str = "",
) -> None:
    """
    Portrait 1080×1920 vertical bar animation.
    0–30f  : X-axis draws left→right
    30–120f: bars grow bottom-up, staggered 0.2 s / 6 frames each
    120–160f: value labels count 0→final
    160–180f: trend line draws left→right
    """
    n       = len(data)
    y_max   = max(data) * 1.3
    TOTAL   = int(round(duration * 30))        # 180
    STAGGER = 6
    BAR_DUR = max(12, (90 - (n - 1) * STAGGER))

    fig, ax = _portrait_fig()
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(0, y_max)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, color=_GRAY, fontsize=8)
    ax.tick_params(colors=_GRAY, length=0)
    ax.set_yticks([])
    ax.set_title(title, fontsize=11, fontweight="bold", color=_TEXT, pad=14)
    if unit:
        ax.set_ylabel(unit, fontsize=8, color=_GRAY, labelpad=6)
    if watermark_text:
        fig.text(0.5, 0.015, watermark_text, ha="center", fontsize=7, color=_GRAY, alpha=0.5)

    for gv in np.linspace(0, y_max * 0.8, 4):
        ax.axhline(gv, color=_GRID, linewidth=0.5, alpha=0.4)

    x_axis, = ax.plot([], [], color=_GRAY, linewidth=1.2, alpha=0.6)
    actual_colors = bar_colors if (bar_colors and len(bar_colors) == n) else [color] * n
    bars = ax.bar(range(n), [0.0] * n, color=actual_colors, alpha=0.85,
                  width=0.55, edgecolor=_BG, linewidth=0.8)
    val_txts = [
        ax.text(i, 0, "", ha="center", va="bottom",
                color=_TEXT, fontsize=9, fontweight="bold")
        for i in range(n)
    ]
    trend_line, = ax.plot([], [], color=_BLUE, linewidth=2.0,
                          linestyle="--", alpha=0.85, zorder=5)
    trend_dots, = ax.plot([], [], "o", color=_BLUE, markersize=5, zorder=6)

    _anno_art = None
    if 0 <= annotation_idx < n and annotation_text:
        _anno_col = (actual_colors[annotation_idx]
                     if actual_colors and annotation_idx < len(actual_colors)
                     else _TEXT)
        _anno_art = ax.text(
            annotation_idx,
            data[annotation_idx] + y_max * 0.10,
            annotation_text,
            ha="center", va="bottom",
            color=_anno_col, fontsize=7, fontweight="bold",
            linespacing=1.3, zorder=7,
            bbox=dict(facecolor=_BG, edgecolor=_anno_col,
                      boxstyle="round,pad=0.25", linewidth=1.5),
            visible=False,
        )

    def update(frame):
        # Phase 1: x-axis
        if frame < 30:
            x_axis.set_data([-0.5, -0.5 + (frame / 30.0) * (n + 0.5)], [0, 0])
        else:
            x_axis.set_data([-0.5, n - 0.5], [0, 0])

        # Phase 2: bars
        for i, (bar, val) in enumerate(zip(bars, data)):
            t0 = 30 + i * STAGGER
            t1 = t0 + BAR_DUR
            frac = 0.0 if frame < t0 else (1.0 if frame >= t1
                   else _anim_ease_out((frame - t0) / BAR_DUR))
            bar.set_height(max(val * frac, 0.0))

        # Phase 3: labels
        for i, (txt, val) in enumerate(zip(val_txts, data)):
            done = 30 + i * STAGGER + BAR_DUR
            if frame < max(done, 120):
                txt.set_text("")
            else:
                p = _anim_ease_out(min((frame - 120) / 40.0, 1.0))
                txt.set_text(_anim_fmt(val * p))
                txt.set_position((i, bars[i].get_height() + y_max * 0.015))

        # Phase 4: trend line
        if frame >= 160:
            p    = min((frame - 160) / 20.0, 1.0)
            nseg = p * (n - 1)
            nf   = int(nseg)
            frac = nseg - nf
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

        if _anno_art is not None:
            _anno_art.set_visible(frame >= 130)

    anim = _manim.FuncAnimation(fig, update, frames=TOTAL, interval=1000 / 30)
    anim.save(output_path, writer=_anim_writer())
    plt.close(fig)


# ── Animated Horizontal Bar (5 s / 150 frames) ───────────────────────────────

def _anim_horizontal_bar(
    data: list, labels: list, title: str,
    highlight_index: int, unit: str,
    output_path: str, duration: float = 5,
    watermark_text: str = "",
) -> None:
    """
    Portrait 1080×1920 horizontal bar animation.
    0–20f  : background
    20–110f: bars extend left→right, staggered 0.3 s / 9 frames each
    110–130f: value labels appear
    130–150f: annotation box flies in from right
    """
    n       = len(data)
    x_max   = max(data) * 1.35
    TOTAL   = int(round(duration * 30))        # 150
    STAGGER = 9
    BAR_DUR = max(12, (90 - (n - 1) * STAGGER))
    hi      = highlight_index

    fig, ax = _portrait_fig()
    ax.set_xlim(0, x_max)
    ax.set_ylim(-0.55, n - 0.45)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, color=_GRAY, fontsize=9)
    ax.tick_params(colors=_GRAY, length=0)
    ax.set_xticks([])
    ax.set_title(title, fontsize=11, fontweight="bold", color=_TEXT, pad=14)
    if watermark_text:
        fig.text(0.5, 0.015, watermark_text, ha="center", fontsize=7, color=_GRAY, alpha=0.5)

    palette  = [_GREEN, _BLUE, "#f0883e", "#bc8cff", _GRAY]
    bar_cols = [
        "#f0883e" if i == hi else palette[i % len(palette)]
        for i in range(n)
    ]
    bars = ax.barh(range(n), [0.0] * n, color=bar_cols,
                   edgecolor=_BG, linewidth=0.8, height=0.55)
    val_txts = [
        ax.text(0, i, "", ha="left", va="center",
                color=_TEXT, fontsize=9, fontweight="bold")
        for i in range(n)
    ]
    _anno_x0 = x_max * 1.6
    _anno_x1 = data[hi] + x_max * 0.03
    anno = ax.text(
        _anno_x0, hi, f"★  {_anim_fmt(data[hi])}{unit}",
        ha="left", va="center", color="#f0883e",
        fontsize=9, fontweight="bold",
        bbox=dict(facecolor=_BG, edgecolor="#f0883e",
                  boxstyle="round,pad=0.3", linewidth=1.5),
    )

    def update(frame):
        for i, (bar, val) in enumerate(zip(bars, data)):
            t0   = 20 + i * STAGGER
            t1   = t0 + BAR_DUR
            frac = (0.0 if frame < t0 else
                    1.0 if frame >= t1 else
                    _anim_ease_out((frame - t0) / BAR_DUR))
            bar.set_width(max(val * frac, 0.0))

        for i, (txt, val) in enumerate(zip(val_txts, data)):
            if frame < 110:
                txt.set_text("")
            else:
                p = _anim_ease_out(min((frame - 110) / 20.0, 1.0))
                txt.set_text(f"{_anim_fmt(val * p)}{unit}")
                txt.set_position((bars[i].get_width() + x_max * 0.01, i))

        if frame >= 130:
            p = _anim_ease_in_out(min((frame - 130) / 20.0, 1.0))
            anno.set_position((_anno_x0 + (_anno_x1 - _anno_x0) * p, hi))

    anim = _manim.FuncAnimation(fig, update, frames=TOTAL, interval=1000 / 30)
    anim.save(output_path, writer=_anim_writer())
    plt.close(fig)


# ── Animated Diverging Bar (7 s / 210 frames) ────────────────────────────────

def _anim_diverging_bar(
    data: list, labels: list, title: str, unit: str,
    output_path: str, duration: float = 7,
    watermark_text: str = "",
) -> None:
    """
    Portrait 1080×1920 diverging bar animation.
    0–30f   : zero axis draws left→right
    30–90f  : negative bars grow downward
    90–150f : positive bars grow upward
    150–180f: turning-point annotation appears
    180–210f: annotation blinks ×3
    """
    n       = len(data)
    abs_max = max(abs(min(data, default=0)), abs(max(data, default=1)), 1.0)
    y_range = abs_max * 1.4
    TOTAL   = int(round(duration * 30))     # 210

    neg_idx = [i for i, v in enumerate(data) if v < 0]
    pos_idx = [i for i, v in enumerate(data) if v >= 0]
    NEG_S   = max(4, 50 // max(len(neg_idx), 1))
    NEG_D   = max(12, 60 - (len(neg_idx) - 1) * NEG_S)
    POS_S   = max(4, 50 // max(len(pos_idx), 1))
    POS_D   = max(12, 60 - (len(pos_idx) - 1) * POS_S)

    turn_idx = next(
        (i for i in range(1, n) if data[i - 1] < 0 and data[i] >= 0),
        pos_idx[0] if pos_idx else None,
    )

    fig, ax = _portrait_fig()
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(-y_range, y_range)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, color=_GRAY, fontsize=8)
    ax.tick_params(colors=_GRAY, length=0)
    ax.set_yticks([])
    ax.set_title(title, fontsize=11, fontweight="bold", color=_TEXT, pad=14)
    if watermark_text:
        fig.text(0.5, 0.015, watermark_text, ha="center", fontsize=7, color=_GRAY, alpha=0.5)

    zero_line, = ax.plot([], [], color=_GRAY, linewidth=1.5, alpha=0.7)
    bar_cols = [_RED if v < 0 else _GREEN for v in data]
    bars = ax.bar(range(n), [0.0] * n, bottom=0.0,
                  color=bar_cols, alpha=0.85, width=0.55,
                  edgecolor=_BG, linewidth=0.8)
    val_txts = [
        ax.text(i, 0, "", ha="center",
                va="top" if v < 0 else "bottom",
                color=_TEXT, fontsize=8, fontweight="bold")
        for i, v in enumerate(data)
    ]
    anno = None
    if turn_idx is not None:
        anno = ax.text(
            turn_idx, data[turn_idx] + y_range * 0.1,
            "↑ 轉正", ha="center", va="bottom",
            color=_BLUE, fontsize=9, fontweight="bold",
            bbox=dict(facecolor=_BG, edgecolor=_BLUE,
                      boxstyle="round,pad=0.3", linewidth=1.5),
            visible=False,
        )

    def _set_bar(i, val, frac):
        h = abs(val) * frac
        if val < 0:
            bars[i].set_y(-h)
            bars[i].set_height(h)
        else:
            bars[i].set_y(0.0)
            bars[i].set_height(h)

    def update(frame):
        # Phase 1: zero axis
        if frame < 30:
            zero_line.set_data([-0.5, -0.5 + (frame / 30.0) * n], [0, 0])
        else:
            zero_line.set_data([-0.5, n - 0.5], [0, 0])

        # Phase 2: negative bars (30–90)
        for j, i in enumerate(neg_idx):
            t0   = 30 + j * NEG_S
            t1   = t0 + NEG_D
            frac = (0.0 if frame < t0 else 1.0 if frame >= t1
                    else _anim_ease_out((frame - t0) / NEG_D))
            _set_bar(i, data[i], frac)

        # Phase 3: positive bars (90–150)
        for j, i in enumerate(pos_idx):
            t0   = 90 + j * POS_S
            t1   = t0 + POS_D
            frac = (0.0 if frame < t0 else 1.0 if frame >= t1
                    else _anim_ease_out((frame - t0) / POS_D))
            _set_bar(i, data[i], frac)

        # Value labels
        for j, (txt, val) in enumerate(zip(val_txts, data)):
            if val < 0:
                done = 30 + neg_idx.index(j) * NEG_S + NEG_D if j in neg_idx else 90
            else:
                done = 90 + pos_idx.index(j) * POS_S + POS_D if j in pos_idx else 150
            if frame >= done:
                sign = "+" if val >= 0 else ""
                txt.set_text(f"{sign}{_anim_fmt(val)}{unit}")
                off = y_range * 0.05
                txt.set_position((j, val - off if val < 0 else val + off * 0.4))
            else:
                txt.set_text("")

        # Phase 4 & 5: annotation
        if anno:
            if frame >= 150:
                anno.set_visible(True)
            if frame >= 180:
                anno.set_visible((frame - 180) % 20 < 10)

    anim = _manim.FuncAnimation(fig, update, frames=TOTAL, interval=1000 / 30)
    anim.save(output_path, writer=_anim_writer())
    plt.close(fig)


# ── Public animated API ───────────────────────────────────────────────────────

def generate_animated_chart(
    chart_data: dict, chart_type: str, output_path: str, duration: float = 6,
) -> None:
    """
    Replaces generate_finance_chart + chart_to_clip.
    Outputs an animated portrait MP4 (1080×1920) directly to output_path.

    Routing:
      eps_trend / candlestick → vertical bar (EPS or revenue)
      revenue_bar             → vertical bar (revenue)
      segment_bar             → horizontal bar (segments)
      gross_margin            → diverging bar (YoY growth)
    """
    company  = chart_data.get("company", "")
    qtrs     = chart_data.get("quarters") or ["Q1", "Q2", "Q3", "Q4"]
    currency = chart_data.get("currency", "")
    unit_str = chart_data.get("unit", "")

    if chart_type in ("eps_trend", "candlestick"):
        raw  = chart_data.get("eps") or chart_data.get("revenue") or [1, 1.5, 2, 2.5]
        data = [float(v) for v in raw[-8:]]
        lbl  = qtrs[-len(data):]
        _anim_vertical_bar(
            data=data, labels=lbl,
            title=f"{company} EPS 趨勢" if company else "EPS 趨勢",
            unit=currency or "NT$",
            color=_GREEN, output_path=output_path, duration=duration,
        )

    elif chart_type == "revenue_bar":
        raw  = chart_data.get("revenue") or [100, 120, 140, 160]
        data = [float(v) for v in raw[-8:]]
        lbl  = qtrs[-len(data):]
        _anim_vertical_bar(
            data=data, labels=lbl,
            title=f"{company} 季營收" if company else "季營收",
            unit=unit_str or "億",
            color=_GREEN, output_path=output_path, duration=duration,
        )

    elif chart_type == "segment_bar":
        segs = chart_data.get("segments") or {"HPC": 52, "Mobile": 33, "IoT": 15}
        vals = [float(v) for v in segs.values()]
        hi   = int(np.argmax(vals))
        _anim_horizontal_bar(
            data=vals, labels=list(segs.keys()),
            title=f"{company} 業務佔比" if company else "業務佔比",
            highlight_index=hi, unit="%",
            output_path=output_path, duration=duration,
        )

    elif chart_type == "gross_margin":
        yoy  = chart_data.get("yoy_growth") or [-5, -2, 2, 5, 8, 12, 15, 18]
        data = [float(v) for v in yoy[-8:]]
        lbl  = qtrs[-len(data):]
        _anim_diverging_bar(
            data=data, labels=lbl,
            title=chart_data.get("chart_title") or (f"{company} 營收年增率" if company else "營收年增率"),
            unit="%", output_path=output_path, duration=duration,
            watermark_text=chart_data.get("chart_watermark", ""),
        )

    else:
        raise ValueError(f"Unknown chart_type '{chart_type}' for animated chart")


def generate_quarterly_comparison_chart(
    data: list, labels: list, title: str, unit: str,
    highlight_index: int, output_path: str,
    highlight_color: str = "#FFD700",
    base_color: str = _BLUE,
    watermark: str = "數據來源：台灣證券交易所",
    duration: float = 6,
    annotation: str = "",
) -> None:
    """Animated vertical bar chart with one highlighted bar (e.g. current quarter)."""
    n = len(data)
    bar_cols = [highlight_color if i == highlight_index else base_color for i in range(n)]
    _anim_vertical_bar(
        data=data, labels=labels, title=title, unit=unit,
        color=base_color, output_path=output_path, duration=duration,
        bar_colors=bar_cols, watermark_text=watermark,
        annotation_idx=highlight_index if annotation else -1,
        annotation_text=annotation,
    )


def generate_highlight_bar_chart(
    data: list, labels: list, title: str, unit: str,
    highlight_index: int, output_path: str,
    watermark: str = "示意圖，非實際數據",
    duration: float = 5,
) -> None:
    """Animated horizontal bar chart with one highlighted bar."""
    _anim_horizontal_bar(
        data=data, labels=labels, title=title,
        highlight_index=highlight_index, unit=unit,
        output_path=output_path, duration=duration,
        watermark_text=watermark,
    )


def generate_etf_dividend_chart(chart_data: dict, output_path: str, duration: float = 5) -> None:
    """Animated horizontal bar for ETF dividend per-unit comparison."""
    div = chart_data.get("etf_dividend", {})
    _anim_horizontal_bar(
        data=div.get("data", [0.6, 1.35]),
        labels=div.get("labels", ["0050 元大台灣50", "0056 元大高股息"]),
        title=div.get("title", "ETF配息金額（元/單位）"),
        highlight_index=div.get("highlight_index", 1),
        unit="元",
        output_path=output_path,
        duration=duration,
        watermark_text=div.get("watermark", "資料來源：投信公告"),
    )


def generate_animated_market_chart(
    narration: str, output_path: str, duration: float = 6, chart_idx: int = 0,
    chart_data: dict | None = None,
) -> None:
    """
    Animated market chart fallback. chart_idx rotates through 3 distinct chart types
    so repeated calls within the same video produce visually different charts.

    idx=0  大盤指數表現       diverging bar (三大指數週漲跌)
    idx=1  牛市年份漲幅       vertical bar  (多頭高峰年 S&P/加權年報酬示意)
    idx=2  散戶 vs 大盤報酬  horizontal bar (一般投資人 vs 指數 vs 法人 示意)
    """
    if chart_data and chart_data.get("quarterly"):
        q = chart_data["quarterly"]
        generate_quarterly_comparison_chart(
            data=q.get("data", []),
            labels=q.get("labels", []),
            title=q.get("title", "季線漲跌幅"),
            unit=q.get("unit", "%"),
            highlight_index=q.get("highlight_index", len(q.get("data", [])) - 1),
            output_path=output_path,
            highlight_color=q.get("highlight_color", "#FFD700"),
            watermark=q.get("watermark", "數據來源：台灣證券交易所"),
            duration=duration,
            annotation=q.get("annotation", ""),
        )
        return

    idx = chart_idx % 3

    if idx == 0:
        try:
            changes, is_demo = _extract_index_changes(narration)
            labels = list(changes.keys())
            values = list(changes.values())
            title  = "大盤指數表現" + ("（示意）" if is_demo else "")
            _anim_horizontal_bar(
                data=[abs(v) for v in values],
                labels=labels,
                title=title,
                highlight_index=int(np.argmax([abs(v) for v in values])),
                unit="%",
                output_path=output_path,
                duration=duration,
            )
        except Exception:
            _anim_horizontal_bar(
                data=[3.5, 4.2, 5.8],
                labels=["道瓊", "標普500", "納斯達克"],
                title="大盤指數（示意）",
                highlight_index=2,
                unit="%",
                output_path=output_path,
                duration=duration,
            )

    elif idx == 1:
        # 牛市高峰年份台股 / S&P 漲幅（示意）
        _anim_vertical_bar(
            data=[26.1, 11.9, 23.7, 27.6, 18.9],
            labels=["2009", "2013", "2017", "2019", "2021"],
            title="牛市年份大盤漲幅（示意）",
            unit="%",
            color=_GREEN,
            output_path=output_path,
            duration=duration,
        )

    else:
        # 散戶 vs 大盤 vs 法人 年化報酬率（示意）
        _anim_horizontal_bar(
            data=[6.2, 12.4, 9.8],
            labels=["散戶投資人", "大盤指數", "法人機構"],
            title="多頭期間年化報酬率（示意）",
            highlight_index=1,
            unit="%",
            output_path=output_path,
            duration=duration,
        )
