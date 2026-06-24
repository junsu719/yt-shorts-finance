import os
import re
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
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


def chart_to_clip(chart_path: str, output_path: str, duration: int = 5):
    """Convert a PNG chart to a 9:16 MP4 with a subtle Ken Burns zoom."""
    total_frames = duration * 30
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
