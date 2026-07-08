import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts

VOICE = "zh-TW-HsiaoChenNeural"
_MIN_SUB_DURATION = 1.5


# ── Public API ────────────────────────────────────────────────────────────────

def synthesize(
    text: str,
    audio_path: str,
    srt_path: str | None = None,
    charts_path: str | None = None,
    voice: str = VOICE,
    rate: str = "+5%",
) -> float:
    """Generate TTS audio and SRT. Returns actual audio duration in seconds.

    If the narration contains [CHARTn] markers and charts_path is provided,
    writes a JSON file mapping "CHART1" → start_timestamp_seconds.
    Markers are stripped before synthesis so they are never spoken aloud.
    """
    clean_text, chart_at = _extract_chart_markers(text)
    return asyncio.run(
        _run(_normalize_for_tts(clean_text), audio_path, srt_path, chart_at, charts_path, voice, rate)
    )


# ── Core: per-sentence synthesis ──────────────────────────────────────────────

async def _run(
    text: str,
    audio_path: str,
    srt_path: str | None,
    chart_at: dict[str, int],
    charts_path: str | None,
    voice: str,
    rate: str,
) -> float:
    """Split narration into sentences, synthesize each, measure with ffprobe,
    concatenate into final audio, then build SRT from real timestamps."""
    sentences = _split_sentences(text)
    if not sentences:
        return 0.0

    tmp_dir = Path(audio_path).parent / "_tts_tmp"
    tmp_dir.mkdir(exist_ok=True)

    seg_paths: list[str] = []
    seg_durations: list[float] = []

    try:
        # Step 1: one MP3 per sentence → ffprobe for actual duration
        for i, sent in enumerate(sentences):
            seg_path = str(tmp_dir / f"s{i:03d}.mp3")
            communicate = edge_tts.Communicate(sent, voice, rate=rate)
            with open(seg_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
            seg_paths.append(seg_path)
            seg_durations.append(_duration(seg_path))

        # Step 2: concatenate all segments into one audio file
        concat_file = tmp_dir / "list.txt"
        concat_file.write_text(
            "\n".join(f"file '{p}'" for p in seg_paths), encoding="utf-8"
        )
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_file), "-c", "copy", audio_path],
            capture_output=True, check=True,
        )

        # Step 3: build SRT where every sentence boundary is a real timestamp
        if srt_path:
            _build_srt_from_segments(sentences, seg_durations, srt_path)

        # Step 4: write chart timestamps derived from sentence-level durations
        if chart_at and charts_path:
            cumulative = [0.0]
            for dur in seg_durations:
                cumulative.append(cumulative[-1] + dur)
            timestamps = {
                marker: round(cumulative[idx], 3)
                for marker, idx in chart_at.items()
                if idx < len(cumulative)
            }
            if timestamps:
                Path(charts_path).write_text(
                    json.dumps(timestamps, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return sum(seg_durations)


# ── SRT builder ───────────────────────────────────────────────────────────────

def _build_srt_from_segments(
    sentences: list[str], durations: list[float], srt_path: str
) -> None:
    """Build SRT using per-sentence actual audio durations as time boundaries.

    Each sentence's start/end time comes from ffprobe measurements (not estimates).
    Long sentences are split into display parts proportionally within that window.
    """
    entries: list[dict] = []
    offset = 0.0

    for sentence, dur in zip(sentences, durations):
        parts = _display_split(sentence)
        total_chars = sum(len(p) for p in parts)
        t = offset
        for part in parts:
            chunk_end = t + (len(part) / total_chars) * dur
            entries.append({"start": t, "end": chunk_end, "text": part})
            t = chunk_end
        offset += dur

    raw = "\n\n".join(
        f"{i + 1}\n{_ts(e['start'])} --> {_ts(e['end'])}\n{e['text']}"
        for i, e in enumerate(entries)
    )
    Path(srt_path).write_text(_merge_short_entries(raw), encoding="utf-8")


# ── Text helpers ──────────────────────────────────────────────────────────────

_CHART_MARKER_RE = re.compile(r"\[CHART(\d+)\]")


def _extract_chart_markers(text: str) -> tuple[str, dict[str, int]]:
    """Strip [CHARTn] markers from narration and record which sentence each precedes.

    Markers may appear inline (e.g. '…每張領600元。[CHART1]除息日…') or on their own
    line — both are handled. Every [CHARTn] occurrence is removed so it is never spoken.

    Returns:
        clean_text  — narration with all [CHARTn] markers removed
        chart_at    — {"CHART1": sentence_index, ...}
                      sentence_index is the 0-based index of the first sentence
                      *after* the marker, matching _split_sentences(clean_text).

    The index is computed by running _split_sentences on the clean text that precedes
    each marker, so it stays consistent with the full-text segmentation used in _run.
    """
    chart_at: dict[str, int] = {}
    clean_parts: list[str] = []
    prefix = ""          # clean text accumulated before the current marker
    last = 0

    for m in _CHART_MARKER_RE.finditer(text):
        segment = text[last:m.start()]
        prefix += segment
        clean_parts.append(segment)
        chart_at[f"CHART{m.group(1)}"] = len(_split_sentences(prefix))
        last = m.end()

    clean_parts.append(text[last:])
    clean_text = "".join(clean_parts)
    # Collapse blank lines left behind by own-line markers.
    clean_text = re.sub(r"[ \t]*\n[ \t]*(?:\n[ \t]*)+", "\n", clean_text).strip()

    return clean_text, chart_at


def _split_sentences(text: str) -> list[str]:
    """Split narration into sentence-level chunks for per-segment TTS."""
    result: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        chunks = [s.strip() for s in re.split(r"(?<=[。！？])", line) if s.strip()]
        result.extend(chunks if chunks else [line])
    return result


def _display_split(sentence: str, threshold: int = 22) -> list[str]:
    """Split a long sentence into two display lines at a natural comma boundary."""
    if len(sentence) <= threshold:
        return [sentence]
    mid = len(sentence) // 2
    for delta in range(mid):
        for i in [mid - delta, mid + delta]:
            if 0 < i < len(sentence) and sentence[i] in "，、":
                return [sentence[:i + 1].strip(), sentence[i + 1:].strip()]
    return [sentence]


def _normalize_for_tts(text: str) -> str:
    """Rewrite symbols that TTS mispronounces into natural Chinese reading."""
    def _pct(m: re.Match) -> str:
        sign, digits = m.group(1), m.group(2)
        return f"{'負' if sign == '-' else ''}百分之{digits}"
    return re.sub(r"[+]?(-?)(\d+(?:\.\d+)?)\s*[%％]", _pct, text)


# ── SRT post-processing ───────────────────────────────────────────────────────

def _merge_short_entries(srt_content: str, min_duration: float = _MIN_SUB_DURATION) -> str:
    """Merge subtitle entries shorter than min_duration into their neighbour."""
    blocks = re.split(r"\n\n+", srt_content.strip())
    entries = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+:\d+:\d+,\d+) --> (\d+:\d+:\d+,\d+)", lines[1])
        if not m:
            continue
        entries.append({
            "start": _parse_ts(m.group(1)),
            "end":   _parse_ts(m.group(2)),
            "text":  "\n".join(lines[2:]),
        })

    if not entries:
        return srt_content

    # Forward pass: short entry merges into the next
    i = 0
    while i < len(entries):
        e = entries[i]
        if e["end"] - e["start"] < min_duration and i + 1 < len(entries):
            nxt = entries[i + 1]
            entries[i + 1] = {
                "start": e["start"],
                "end":   nxt["end"],
                "text":  e["text"].rstrip() + nxt["text"].lstrip(),
            }
            entries.pop(i)
        else:
            i += 1

    # Backward pass: short final entry merges into previous
    if len(entries) >= 2 and entries[-1]["end"] - entries[-1]["start"] < min_duration:
        last = entries.pop()
        entries[-1]["end"]  = last["end"]
        entries[-1]["text"] = entries[-1]["text"].rstrip() + last["text"].lstrip()

    return "\n\n".join(
        f"{idx}\n{_ts(e['start'])} --> {_ts(e['end'])}\n{e['text']}"
        for idx, e in enumerate(entries, 1)
    )


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _parse_ts(ts: str) -> float:
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", path],
        capture_output=True, text=True, check=True,
    )
    streams = json.loads(result.stdout).get("streams", [])
    return float(streams[0]["duration"]) if streams else 0.0
