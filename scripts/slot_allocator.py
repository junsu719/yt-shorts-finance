"""slot_allocator.py — Dynamic slot plan from SRT + chart timestamps.

Public API:
    SlotSpec         — dataclass describing one video or chart slot
    build_slot_plan  — SRT + charts JSON → List[SlotSpec]
    print_slot_table — print human-readable slot timeline to stdout
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

_CHART_DURATION   = 8.0   # seconds reserved per chart slot (animation length)
_MIN_CHART_DUR    = 4.0   # discard chart slots shorter than this (too close to end)
_MAX_VIDEO_SLOT   = 12.0  # hard upper bound for a single video slot (seconds)
_VIDEO_SOURCES    = ["pexels", "pixabay", "mixkit", "vecteezy"]

# Proportional chart positions used when narration_charts.json is absent.
# 30 % / 55 % / 75 % of total duration (user-specified fallback).
_FALLBACK_POSITIONS: dict[str, list[float]] = {
    "education": [0.30, 0.55, 0.75],
    "earnings":  [0.33, 0.66],
    "market":    [0.40],
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class SlotSpec:
    index:    int    # 1-based slot number
    start:    float  # seconds from video start
    end:      float  # seconds
    duration: float  # = end - start
    type:     str    # "video" | "chart"
    source:   str    # "pexels"/"pixabay"/"mixkit"/"vecteezy" — empty for chart
    query:    str    # stock-footage search keyword — empty for chart


# ── SRT helpers ───────────────────────────────────────────────────────────────

def _parse_srt_duration(srt_path: str) -> float:
    """Return the end timestamp of the last SRT entry in seconds."""
    text = Path(srt_path).read_text(encoding="utf-8")
    # Capture the end time of every "start --> end" timestamp line
    matches = re.findall(r"\d+:\d+:\d+,\d+\s*-->\s*(\d+:\d+:\d+,\d+)", text)
    return _ts_to_sec(matches[-1]) if matches else 0.0


def _ts_to_sec(ts: str) -> float:
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


# ── Chart timestamp loading ───────────────────────────────────────────────────

def _load_chart_timestamps(
    charts_path: str | None,
    total_duration: float,
    content_type: str,
) -> list[float]:
    """Return sorted list of chart start timestamps (seconds).

    Reads narration_charts.json when available; otherwise falls back to
    proportional positions defined in _FALLBACK_POSITIONS.
    """
    if charts_path:
        p = Path(charts_path)
        if p.exists() and p.stat().st_size > 2:
            try:
                data: dict[str, float] = json.loads(p.read_text(encoding="utf-8"))
                ts_list = sorted(data.values())
                if ts_list:
                    return ts_list
            except Exception:
                pass

    fractions = _FALLBACK_POSITIONS.get(content_type, [])
    return [round(total_duration * f, 3) for f in fractions]


# ── Core builder ──────────────────────────────────────────────────────────────

def build_slot_plan(
    srt_path: str,
    charts_path: str | None,
    search_queries: list[str],
    content_type: str,
) -> list[SlotSpec]:
    """Build a time-accurate slot plan for the full video.

    Algorithm
    ---------
    1. Parse SRT → total_duration.
    2. Load chart timestamps (narration_charts.json or proportional fallback).
    3. Place chart slots at those timestamps (each 8 s, clamped to video end).
    4. Fill gaps between / before / after chart slots with video slots (≤ 12 s each).
    5. Cycle sources: pexels → pixabay → mixkit → vecteezy (video slots only).
    6. Cycle search_queries per video slot.
    """
    total_duration = _parse_srt_duration(srt_path)
    if total_duration < 1.0:
        fallback_q = search_queries[0] if search_queries else "stock market"
        return [SlotSpec(1, 0.0, 60.0, 60.0, "video", "pexels", fallback_q)]

    raw_timestamps = _load_chart_timestamps(charts_path, total_duration, content_type)

    # ── Build chart intervals [cs, ce], clamped and merged ────────────────────
    chart_ivs: list[list[float]] = []
    for ts in sorted(raw_timestamps):
        cs = round(max(0.0, ts), 3)
        ce = round(min(total_duration, ts + _CHART_DURATION), 3)
        if ce - cs < _MIN_CHART_DUR:
            continue                       # chart too short (too close to end)
        if chart_ivs and cs < chart_ivs[-1][1]:
            chart_ivs[-1][1] = max(chart_ivs[-1][1], ce)   # merge overlapping
        else:
            chart_ivs.append([cs, ce])

    # ── Assemble slots ────────────────────────────────────────────────────────
    slots: list[SlotSpec] = []
    video_count = 0

    def _add_video_slots(gap_start: float, gap_end: float) -> None:
        nonlocal video_count
        gap = round(gap_end - gap_start, 3)
        if gap < 0.5:
            return
        # Split into n evenly-sized slots, each ≤ _MAX_VIDEO_SLOT
        n   = max(1, math.ceil(gap / _MAX_VIDEO_SLOT))
        dur = gap / n
        t   = gap_start
        for _ in range(n):
            s_end  = round(min(t + dur, gap_end), 3)
            source = _VIDEO_SOURCES[video_count % len(_VIDEO_SOURCES)]
            query  = (search_queries[video_count % len(search_queries)]
                      if search_queries else "stock market")
            slots.append(SlotSpec(
                index    = 0,            # renumbered below
                start    = round(t, 3),
                end      = s_end,
                duration = round(s_end - t, 3),
                type     = "video",
                source   = source,
                query    = query,
            ))
            video_count += 1
            t = s_end

    # Walk timeline: [gap → chart] × N → trailing gap
    cursor = 0.0
    for cs, ce in chart_ivs:
        _add_video_slots(cursor, cs)
        slots.append(SlotSpec(
            index    = 0,
            start    = cs,
            end      = ce,
            duration = round(ce - cs, 3),
            type     = "chart",
            source   = "",
            query    = "",
        ))
        cursor = ce

    _add_video_slots(cursor, total_duration)

    # Assign sequential 1-based indices
    for i, s in enumerate(slots):
        s.index = i + 1

    return slots


# ── Display helpers ───────────────────────────────────────────────────────────

def _sec_to_ts(seconds: float) -> str:
    """Format seconds as MM:SS.ss for the slot table."""
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"


def print_slot_table(
    slots: list[SlotSpec],
    total_duration: float,
    topic: str = "",
) -> None:
    """Print a human-readable slot timeline to stdout."""
    n_chart = sum(1 for s in slots if s.type == "chart")
    n_video = len(slots) - n_chart

    title = "Slot 時間對照表"
    if topic:
        title += f"（{topic}）"
    title += f"，總時長 {total_duration:.1f}s，共 {len(slots)} 個 Slot"

    sep = "=" * 74
    print()
    print(title)
    print(sep)
    for s in slots:
        kind = "CHART" if s.type == "chart" else "video"
        src  = s.source if s.source else "---"
        q    = s.query[:32] + "..." if len(s.query) > 35 else s.query
        print(
            f"Slot {s.index:02d} | "
            f"{_sec_to_ts(s.start)} - {_sec_to_ts(s.end)} | "
            f"{s.duration:5.1f}s | "
            f"{kind:<5} | {src:<8} | {q}"
        )
    print(sep)
    print(f"  影片 Slot: {n_video}  |  圖表 Slot: {n_chart}  |  合計: {len(slots)} 個")
