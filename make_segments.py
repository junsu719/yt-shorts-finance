"""
make_segments.py  —  16:9 教學長片逐段製作工具
Usage: python make_segments.py --step <1|2|3|4|all>
"""
import argparse, os, subprocess, sys, textwrap
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("config/.env")
OUT = Path("output/memory_segments")
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1920, 1080   # 16:9

# ── 腳本文字 ──────────────────────────────────────────────────────────────────
SEGMENTS = {
    1: "你有沒有發現，最近台股有幾檔股票一直在創新高，而且漲幅嚇死人？它們有個共同點：都是做記憶體的。但記憶體到底是什麼？為什麼突然這麼強？今天三分鐘幫你搞懂。",
    2: "你的電腦和手機裡面，有兩種地方可以存東西。一種是硬碟，像你家的倉庫，東西放進去不會消失，但找起來比較慢。另一種是記憶體，像你的書桌，正在用的東西放上面，速度很快，但關機就清空了。AI在運算的時候，需要超級大的書桌，這就是為什麼AI爆發，記憶體需求跟著爆。記憶體有三種你需要知道：DRAM，電腦和伺服器用的，速度快；NAND Flash，手機和SSD用的，可以永久存資料；還有HBM，也叫高頻寬記憶體，專門為AI設計，塞進AI晶片旁邊，速度是普通記憶體的好幾倍。",
    3: "訓練一個大型AI模型，需要同時處理海量的數據，這些數據都要先放進記憶體裡才能運算。ChatGPT、Gemini、Claude這些AI，背後跑的伺服器每一台都需要大量HBM。全球AI伺服器瘋狂擴建，記憶體需求就像開了水龍頭關不掉。偏偏HBM製作難度極高，全球只有三家公司做得出來：美國的美光、韓國的三星和SK海力士。",
    4: "美光是全球三大記憶體廠之一，也是唯一一家美國本土記憶體公司。在AI需求爆發之前，記憶體是很景氣循環的產業，常常大起大落。但這一波不一樣，美光的HBM產能已經賣到2026年底全部售罄，今年EPS預估年增超過九倍，股價從年初到現在漲了將近三倍。",
    5: "台灣雖然沒有直接做HBM，但有很多公司在這條供應鏈上。南亞科和華邦電，做的是一般DRAM，隨著整體記憶體供需改善跟著受惠。創見、群聯、廣穎、威剛，做的是記憶體模組和儲存裝置，屬於下游應用端。這些公司不是直接做AI記憶體，但市場資金輪動時，常常會一起被帶動。",
    6: "記憶體產業從景氣谷底到現在的爆發，核心就是一件事：AI需求結構性改變了。今晚美光財報公布，追蹤頻道，我們第一時間為你解析結果！本影片僅供教育用途，不構成投資建議。",
}

# ── Slot 背景素材設定 ─────────────────────────────────────────────────────────
SLOTS = {
    1: {"type": "photo",  "src": "assets/custom/micron.jpg"},
    2: {"type": "chart",  "src": str(OUT / "hbm_chart.png")},
    3: {"type": "video",  "source": "pixabay",  "query": "memory chip semiconductor"},
    4: {"type": "video",  "source": "pexels",   "query": "semiconductor memory chip"},
    5: {"type": "photo",  "src": "assets/custom/memory_frog.jpg"},
    6: {"type": "video",  "source": "mixkit",   "query": "technology semiconductor"},
    7: {"type": "video",  "source": "vecteezy", "query": "memory chip circuit"},
}

# ── Step 1: HBM 圖表 ──────────────────────────────────────────────────────────
def step1_chart():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    BG   = "#1a1a2e"
    GRN  = "#00ff88"
    RED  = "#ff4444"
    WHT  = "#e0e0e0"
    GRID = "#2a2a4a"

    # 直接用字型檔路徑，繞過 matplotlib 字型快取問題
    FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
    fp_bold = fm.FontProperties(fname=FONT_PATH, size=36)
    fp_md   = fm.FontProperties(fname=FONT_PATH, size=22)
    fp_sm   = fm.FontProperties(fname=FONT_PATH, size=16)
    fp_lg   = fm.FontProperties(fname=FONT_PATH, size=20)

    fig, ax = plt.subplots(figsize=(W/100, H/100), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    years   = [2024, 2025, 2026, 2027]
    demand  = [100, 210, 390, 620]   # 示意：陡升
    supply  = [100, 150, 220, 310]   # 示意：緩升

    ax.fill_between(years, supply, demand, color=RED, alpha=0.25, label="_gap")
    ax.plot(years, demand, color=RED,  linewidth=4, marker="o", markersize=10,
            label="需求量（AI驅動）", zorder=3)
    ax.plot(years, supply, color=GRN,  linewidth=4, marker="s", markersize=10,
            label="供給量（擴產受限）", zorder=3)

    # 缺口標註
    mid_y = (demand[2] + supply[2]) / 2
    ax.annotate("供需缺口", xy=(2026, mid_y),
                fontproperties=fm.FontProperties(fname=FONT_PATH, size=22),
                color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=2),
                xytext=(2025.3, mid_y + 60))

    ax.set_xlim(2023.7, 2027.3)
    ax.set_ylim(40, 720)
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=22, color=WHT)
    ax.set_yticks([])
    ax.tick_params(colors=WHT, length=0)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.yaxis.set_visible(False)
    ax.grid(axis="x", color=GRID, linewidth=0.5)

    ax.set_title("AI 爆發帶動 HBM 供不應求", fontproperties=fp_bold,
                 color=WHT, pad=28)

    legend = ax.legend(fontsize=20, facecolor=BG, edgecolor=GRID,
                       labelcolor=WHT, loc="upper left",
                       prop=fp_lg)

    ax.text(0.5, -0.08, "示意圖，非實際數據",
            transform=ax.transAxes, fontproperties=fp_sm,
            color="#888888", ha="center")

    out_png = OUT / "hbm_chart.png"
    plt.tight_layout(pad=1.5)
    plt.savefig(out_png, dpi=100, facecolor=BG)
    plt.close()
    print(f"[Step 1] 圖表已輸出：{out_png}  ({W}×{H})")
    return str(out_png)

# ── Step 2: TTS 逐段配音 ──────────────────────────────────────────────────────
def step2_tts():
    sys.path.insert(0, "scripts")
    from tts import synthesize

    out_abs = OUT.resolve()
    for seg_id, text in SEGMENTS.items():
        audio_path = str(out_abs / f"audio_{seg_id:02d}.mp3")
        srt_path   = str(out_abs / f"sub_{seg_id:02d}.srt")
        dur = synthesize(text, audio_path, srt_path)
        print(f"[Step 2] 段落 {seg_id}：audio_{seg_id:02d}.mp3  ({dur:.1f}s)")

# ── Step 3: 素材下載 ──────────────────────────────────────────────────────────
def _encode_landscape(url: str, out_path: str) -> bool:
    """Download and re-encode to 1920×1080 landscape."""
    import tempfile, hashlib, requests
    tmp = out_path + ".tmp.mp4"
    try:
        r = requests.get(url, timeout=30, stream=True)
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
    except Exception as e:
        print(f"  [dl] 下載失敗：{e}")
        return False

    cmd = [
        "ffmpeg", "-y", "-i", tmp,
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
        "-t", "25",
        "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-an",
        "-loglevel", "error",
        out_path,
    ]
    ret = subprocess.run(cmd)
    Path(tmp).unlink(missing_ok=True)
    if ret.returncode != 0:
        print(f"  [enc] FFmpeg 失敗")
        return False
    size_kb = Path(out_path).stat().st_size // 1024
    print(f"  → {out_path}  ({size_kb} KB)")
    return True

def step3_videos():
    sys.path.insert(0, "scripts")
    import video_gen as vg

    seen_ids    = set()
    seen_hashes = set()

    for slot_id, cfg in SLOTS.items():
        if cfg["type"] != "video":
            print(f"[Step 3] Slot {slot_id}: 非影片素材，跳過")
            continue

        out_path = str(OUT / f"bg_{slot_id:02d}.mp4")
        if Path(out_path).exists():
            print(f"[Step 3] Slot {slot_id}: 已存在，跳過")
            continue

        query  = cfg["query"]
        source = cfg["source"]
        print(f"[Step 3] Slot {slot_id} [{source}] query='{query}'")

        # 取得影片 URL（使用 video_gen 的搜尋，但自訂編碼解析度）
        url = None
        for _ in range(5):
            url = vg._resolve_url(query, source, seen_ids)
            if url:
                break
        if not url:
            for fallback in ["stock market", "technology background"]:
                url = vg._resolve_url(fallback, "auto", seen_ids)
                if url:
                    break

        if url:
            _encode_landscape(url, out_path)
        else:
            print(f"  [Step 3] Slot {slot_id}: 找不到素材")

# ── Step 4: 相片轉影片（Ken Burns，1920×1080） ────────────────────────────────
def step4_photos():
    for slot_id, cfg in SLOTS.items():
        if cfg["type"] not in ("photo", "chart"):
            continue

        src = cfg["src"]
        if not Path(src).exists():
            print(f"[Step 4] Slot {slot_id}: 找不到 {src}")
            continue

        out_path = str(OUT / f"bg_{slot_id:02d}.mp4")
        # 刪除舊的失敗輸出（由 fallback 產生的黑邊版）
        if Path(out_path).exists():
            Path(out_path).unlink()

        info_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "csv=p=0", src]
        result = subprocess.run(info_cmd, capture_output=True, text=True)
        try:
            pw, ph = map(int, result.stdout.strip().split(","))
        except Exception:
            pw, ph = W, H

        ratio = pw / ph
        target_ratio = W / H

        if abs(ratio - target_ratio) < 0.05:
            # 已是 16:9（如 hbm_chart.png 1920×1080）：直接加 Ken Burns
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", src,
                "-t", "25", "-r", "30",
                "-vf", (f"scale={W}:{H},"
                        f"zoompan=z='min(zoom+0.0005,1.08)':x='iw/2-(iw/zoom/2)':"
                        f"y='ih/2-(ih/zoom/2)':d=750:s={W}x{H}:fps=30"),
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-an", "-loglevel", "error", out_path,
            ]
        elif ratio > target_ratio:
            # 超寬：縮放 + crop 填滿 + Ken Burns
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", src,
                "-t", "25", "-r", "30",
                "-vf", (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                        f"crop={W}:{H},"
                        f"zoompan=z='min(zoom+0.0005,1.12)':x='iw/2-(iw/zoom/2)':"
                        f"y='ih/2-(ih/zoom/2)':d=750:s={W}x{H}:fps=30"),
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-an", "-loglevel", "error", out_path,
            ]
        else:
            # 窄於 16:9（含直式）：模糊背景 + 清晰圖置中，-filter_complex
            fg_scale = f"scale=-2:{H}" if ratio < 1 else f"scale={W}:-2"
            fc = (
                f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},boxblur=25:5[bg];"
                f"[0:v]{fg_scale}[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
            )
            cmd = [
                "ffmpeg", "-y", "-loop", "1", "-i", src,
                "-t", "25", "-r", "30",
                "-filter_complex", fc,
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-an", "-loglevel", "error", out_path,
            ]

        ret = subprocess.run(cmd)
        if ret.returncode == 0:
            size_kb = Path(out_path).stat().st_size // 1024
            print(f"[Step 4] Slot {slot_id} ({pw}×{ph}, ratio={ratio:.2f}) → {out_path}  ({size_kb} KB)")
        else:
            print(f"[Step 4] Slot {slot_id}: 失敗，用黑邊 fallback")
            cmd_fb = [
                "ffmpeg", "-y", "-loop", "1", "-i", src,
                "-t", "25", "-r", "30",
                "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#1a1a2e",
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-an", "-loglevel", "error", out_path,
            ]
            ret2 = subprocess.run(cmd_fb)
            if ret2.returncode == 0:
                print(f"[Step 4] Slot {slot_id}: fallback 完成")

# ── Step 5: 組合各段 MP4 ─────────────────────────────────────────────────────
def step5_assemble():
    # 段落 ↔ slot 對應（段落 6 用 slot 6，警語片段用 slot 7 但同音訊）
    SEG_SLOT = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}
    FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

    for seg_id in range(1, 8):
        # slot 7 = 用 slot 6 段落的後半（警語），這裡直接用 bg_07 + audio_06
        audio_seg = min(seg_id, 6)
        audio_path = OUT / f"audio_{audio_seg:02d}.mp3"
        bg_path    = OUT / f"bg_{seg_id:02d}.mp4"
        srt_path   = OUT / f"sub_{audio_seg:02d}.srt"
        out_path   = OUT / f"segment_{seg_id:02d}.mp4"

        if not audio_path.exists():
            print(f"[Step 5] Segment {seg_id}: 缺 {audio_path}，跳過")
            continue
        if not bg_path.exists():
            print(f"[Step 5] Segment {seg_id}: 缺 {bg_path}，跳過")
            continue

        # 取得音訊時長
        dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", str(audio_path)]
        dur_out = subprocess.run(dur_cmd, capture_output=True, text=True).stdout.strip()
        try:
            dur = float(dur_out)
        except Exception:
            dur = 30.0

        # 字幕濾鏡
        srt_filter = ""
        if srt_path.exists():
            srt_esc = str(srt_path).replace(":", "\\:")
            srt_filter = (
                f",subtitles={srt_esc}:force_style='"
                f"Fontname=Noto Sans CJK TC,FontSize=28,Bold=1,"
                f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                f"Outline=2,Shadow=1,Alignment=2,MarginV=60'"
            )

        vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black{srt_filter}"

        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(bg_path),
            "-i", str(audio_path),
            "-t", str(dur),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-loglevel", "error",
            str(out_path),
        ]
        ret = subprocess.run(cmd)
        if ret.returncode == 0:
            size_mb = Path(out_path).stat().st_size // (1024*1024)
            print(f"[Step 5] segment_{seg_id:02d}.mp4  ({dur:.1f}s, {size_mb} MB)")
        else:
            print(f"[Step 5] Segment {seg_id}: FFmpeg 失敗")

# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", default="all",
                    choices=["1","2","3","4","5","all"])
    args = ap.parse_args()

    steps = ["1","2","3","4","5"] if args.step == "all" else [args.step]
    if "1" in steps: step1_chart()
    if "2" in steps: step2_tts()
    if "3" in steps: step3_videos()
    if "4" in steps: step4_photos()
    if "5" in steps: step5_assemble()
