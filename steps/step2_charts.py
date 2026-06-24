"""Step 2：用 matplotlib 生成三張教學圖表"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams['axes.unicode_minus'] = False
from matplotlib.patches import FancyBboxPatch
from matplotlib.font_manager import FontProperties
import numpy as np

BASE_DIR   = Path(__file__).parent.parent
CHARTS_DIR = BASE_DIR / "charts"

BG       = "#1a1a2e"
GREEN    = "#00ff88"
RED      = "#ff4444"
GRAY     = "#888888"
WHITE    = "#ffffff"
DIMWHITE = "#cccccc"
YELLOW   = "#ffdd57"
DISCLAIMER = "數字僅供教學示範"

# 直接指定字體檔案路徑，繞過名稱解析，確保繁體中文正確顯示
_CJK_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]
_FONT_PATH = next((p for p in _CJK_CANDIDATES if Path(p).exists()), None)
FONT_PROP  = FontProperties(fname=_FONT_PATH) if _FONT_PATH else FontProperties()
FONT       = FONT_PROP   # 供外部查詢用


def _apply_base_style(fig, ax):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=DIMWHITE, labelsize=14)


def _chart1(config: dict) -> Path:
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    _apply_base_style(fig, ax)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    ax.text(5, 5.5, "財報四大組成", ha="center", va="center",
            fontsize=38, fontweight="bold", color=GREEN, fontproperties=FONT_PROP)

    boxes = [
        (1.2, 3.0, "損益表",        "Income Statement", "這季賺了多少錢"),
        (3.6, 3.0, "資產負債表",    "Balance Sheet",    "有多少家當 / 欠多少債"),
        (6.0, 3.0, "現金流量表",    "Cash Flow",        "錢有沒有真的進來"),
        (8.4, 3.0, "股東權益\n變動表", "Equity Changes", "股東的錢有沒有變多"),
    ]
    for x, y, zh, en, desc in boxes:
        rect = FancyBboxPatch((x - 0.95, y - 0.8), 1.9, 1.6,
                              boxstyle="round,pad=0.08",
                              linewidth=2, edgecolor=GREEN, facecolor="#0d2d1f")
        ax.add_patch(rect)
        ax.text(x, y + 0.35, zh,   ha="center", va="center",
                fontsize=20, fontweight="bold", color=GREEN, fontproperties=FONT_PROP)
        ax.text(x, y - 0.05, en,   ha="center", va="center",
                fontsize=11, color=DIMWHITE, fontproperties=FONT_PROP)
        ax.text(x, y - 0.50, desc, ha="center", va="center",
                fontsize=13, color=WHITE, fontproperties=FONT_PROP)

    for x_start, x_end in [(2.15, 2.65), (4.55, 5.05), (6.95, 7.45)]:
        ax.annotate("", xy=(x_end, 3.0), xytext=(x_start, 3.0),
                    arrowprops=dict(arrowstyle="->", color=GREEN, lw=2))

    ax.text(5, 1.5, "每三個月公布一次，合稱「財務報告」（財報）",
            ha="center", va="center", fontsize=18, color=DIMWHITE, fontproperties=FONT_PROP)
    ax.text(9.6, 0.15, DISCLAIMER, ha="right", va="bottom",
            fontsize=11, color=GRAY, fontproperties=FONT_PROP)

    path = CHARTS_DIR / "chart1_four_statements.png"
    fig.savefig(path, dpi=100, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def _chart2(config: dict) -> Path:
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    _apply_base_style(fig, ax)

    scenarios     = ["超預期", "符合預期", "低於預期"]
    expected      = [3.8, 4.0, 4.2]
    actual        = [4.2, 4.0, 3.5]
    colors_actual = [GREEN, YELLOW, RED]

    x     = np.arange(len(scenarios))
    width = 0.32

    bars_e = ax.bar(x - width/2, expected, width, label="市場預期 EPS",
                    color="#2a4a3a", edgecolor=GREEN, linewidth=1.5)
    bars_a = ax.bar(x + width/2, actual,   width, label="實際 EPS",
                    color=colors_actual, edgecolor=WHITE, linewidth=1.2)

    for bar in bars_e:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.08,
                f"{bar.get_height():.1f}", ha="center", va="bottom",
                color=DIMWHITE, fontsize=15, fontproperties=FONT_PROP)
    for bar, col in zip(bars_a, colors_actual):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.08,
                f"{bar.get_height():.1f}", ha="center", va="bottom",
                color=col, fontsize=16, fontweight="bold", fontproperties=FONT_PROP)

    outcomes       = ["▲ 股價大漲", "→ 視展望而定", "▼ 股價大跌"]
    outcome_colors = [GREEN, YELLOW, RED]
    for i, (label, col) in enumerate(zip(outcomes, outcome_colors)):
        ax.text(i, -0.45, label, ha="center", va="top",
                color=col, fontsize=16, fontweight="bold", fontproperties=FONT_PROP)

    ax.set_title("市場預期 vs 實際 EPS：三種情境",
                 fontsize=32, fontweight="bold", color=WHITE, pad=20, fontproperties=FONT_PROP)
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=20, color=WHITE, fontproperties=FONT_PROP)
    ax.set_ylabel("EPS（元）", fontsize=16, color=DIMWHITE, fontproperties=FONT_PROP)
    ax.set_ylim(0, 5.2)
    ax.yaxis.label.set_color(DIMWHITE)
    ax.tick_params(axis="y", colors=DIMWHITE)

    legend = ax.legend(fontsize=15, facecolor="#0d1b2a", edgecolor=GREEN, labelcolor=WHITE)
    plt.setp(legend.get_texts(), fontproperties=FONT_PROP)
    ax.text(0.98, 0.02, DISCLAIMER, transform=ax.transAxes,
            ha="right", va="bottom", fontsize=11, color=GRAY, fontproperties=FONT_PROP)

    path = CHARTS_DIR / "chart2_eps_comparison.png"
    fig.savefig(path, dpi=100, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def _chart3(config: dict) -> Path:
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    _apply_base_style(fig, ax)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis("off")

    ax.text(6, 3.65, "全年財報季時間軸", ha="center", va="center",
            fontsize=36, fontweight="bold", color=GREEN, fontproperties=FONT_PROP)

    ax.annotate("", xy=(11.8, 1.8), xytext=(0.2, 1.8),
                arrowprops=dict(arrowstyle="->", color=DIMWHITE, lw=2))

    for m in range(1, 13):
        ax.plot([m, m], [1.7, 1.9], color=DIMWHITE, lw=1.2)
        ax.text(m, 1.55, f"{m}月", ha="center", va="top",
                fontsize=13, color=DIMWHITE, fontproperties=FONT_PROP)

    seasons = [
        (4.5,  5.9,  "Q1 財報季\n4月中－5月底"),
        (7.5,  8.9,  "Q2 財報季\n7月中－8月底"),
        (10.5, 11.9, "Q3 財報季\n10月中－11月底"),
        (1.5,  2.9,  "Q4 財報季\n1月中－2月底"),
    ]
    label_y = [2.85, 3.2, 2.85, 3.2]

    for (start, end, label), y_lbl in zip(seasons, label_y):
        rect = plt.Rectangle((start, 1.88), end - start, 0.28,
                              facecolor=GREEN, alpha=0.85, zorder=3)
        ax.add_patch(rect)
        mid = (start + end) / 2
        ax.text(mid, y_lbl, label, ha="center", va="center",
                fontsize=13, fontweight="bold", color=WHITE, fontproperties=FONT_PROP,
                bbox=dict(facecolor="#0d2d1f", edgecolor=GREEN,
                          boxstyle="round,pad=0.3", linewidth=1.5))
        ax.plot([mid, mid], [2.16, y_lbl - 0.18],
                color=GREEN, lw=1.2, linestyle="--", alpha=0.7)

    ax.text(6, 1.1, "灰色空窗期：市場相對平靜，等待下一個財報季",
            ha="center", va="center", fontsize=15, color=GRAY, fontproperties=FONT_PROP)
    ax.text(11.6, 0.25, DISCLAIMER, ha="right", va="bottom",
            fontsize=11, color=GRAY, fontproperties=FONT_PROP)

    path = CHARTS_DIR / "chart3_earnings_calendar.png"
    fig.savefig(path, dpi=100, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


_GENERATORS = {1: _chart1, 2: _chart2, 3: _chart3}


def generate_chart(chart_id: int, config: dict) -> Path:
    note = config.get(f"chart{chart_id}_note", "")
    if note:
        print(f"[圖表{chart_id}] 套用修改意見：{note}")
    return _GENERATORS[chart_id](config)
