#!/usr/bin/env python3
"""
Fix: concat all clip videos (no audio) → pad to narration length
     → overlay full narration.mp3 → burn narration.srt → output final.mp4

Step A: concat video tracks only           → bg_noaudio.mp4
Step B: tpad last frame to fill narr gap   → bg_padded.mp4
Step C+D: overlay narration.mp3 + subtitles → risk_education_final.mp4
"""
import os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, '/home/junsu/yt-shorts-finance')

BASE     = Path('/mnt/d/yt-shorts-finance/output/risk_education_segments')
NARR_MP3 = str(BASE / 'narration.mp3')
NARR_SRT = str(BASE / 'narration.srt')
FINAL    = str(BASE / 'risk_education_final.mp4')

# Intermediates (cleaned up at end)
LIST_TXT    = str(BASE / 'concat_video_only.txt')
BG_NOAUDIO  = str(BASE / '_bg_noaudio.mp4')
BG_PADDED   = str(BASE / '_bg_padded.mp4')
NARR_ASS    = str(BASE / '_narration_landscape.ass')


# ── helpers ───────────────────────────────────────────────────────────────────

def run(cmd, desc=''):
    if desc:
        print(f'  {desc}...', flush=True)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_duration(path):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1', path],
        capture_output=True, text=True, check=True)
    return float(r.stdout.strip().split('=')[1])


def get_size(path):
    return Path(path).stat().st_size


# ── SRT → landscape ASS ───────────────────────────────────────────────────────

_ASS_HEADER = (
    "[Script Info]\n"
    "ScriptType: v4.00+\n"
    "PlayResX: 1920\n"
    "PlayResY: 1080\n"
    "WrapStyle: 2\n\n"
    "[V4+ Styles]\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
    "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
    "Alignment, MarginL, MarginR, MarginV, Encoding\n"
    "Style: Default,Noto Sans CJK TC,48,&H00FFFFFF,&H000000FF,"
    "&H00000000,&H80000000,1,0,0,0,100,100,0,0,3,3,1,2,60,60,50,1\n\n"
    "[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
)


def _ts_to_sec(ts):
    h, m, rest = ts.split(':')
    s, ms = rest.split(',')
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000


def _sec_to_ass(sec):
    sec = max(0.0, sec)
    h = int(sec // 3600);  sec -= h*3600
    m = int(sec // 60);    sec -= m*60
    s = int(sec)
    cs = int((sec - s) * 100)
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'


def srt_to_ass(srt_path, ass_path):
    text   = Path(srt_path).read_text(encoding='utf-8')
    blocks = re.split(r'\n\n+', text.strip())
    dialogues = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        m = re.match(r'(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)', lines[1])
        if not m:
            continue
        start = _sec_to_ass(_ts_to_sec(m.group(1)))
        end   = _sec_to_ass(_ts_to_sec(m.group(2)))
        body  = r'\N'.join(lines[2:])
        dialogues.append(f'Dialogue: 0,{start},{end},Default,,0,0,0,,{body}')
    Path(ass_path).write_text(
        _ASS_HEADER + '\n'.join(dialogues) + '\n', encoding='utf-8'
    )
    print(f'  ASS subtitle: {len(dialogues)} entries')


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print('=== Fix: concat video + full narration + subtitles ===\n')

    # ── Step A: concat all 23 clip video tracks (strip audio) ─────────────────
    print('Step A — concat 23 clip videos (video only)...')
    list_lines = [
        f"file '{BASE}/clip_{i:02d}.mp4'"
        for i in range(1, 24)
    ]
    Path(LIST_TXT).write_text('\n'.join(list_lines) + '\n', encoding='utf-8')

    run(
        ['ffmpeg', '-y',
         '-f', 'concat', '-safe', '0', '-i', LIST_TXT,
         '-an',               # strip all audio
         '-c:v', 'copy',      # no re-encode
         BG_NOAUDIO],
        'FFmpeg concat video-only',
    )
    bg_dur   = get_duration(BG_NOAUDIO)
    narr_dur = get_duration(NARR_MP3)
    gap      = narr_dur - bg_dur
    print(f'  video concat: {bg_dur:.3f}s')
    print(f'  narration:    {narr_dur:.3f}s')
    print(f'  gap to fill:  {gap:.3f}s')

    # ── Step B: pad last frame to fill gap ────────────────────────────────────
    print('\nStep B — pad last frame to match narration duration...')
    if gap > 0.1:
        run(
            ['ffmpeg', '-y', '-i', BG_NOAUDIO,
             '-vf', f'tpad=stop_duration={gap:.3f}:stop_mode=clone',
             '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
             '-an',
             BG_PADDED],
            f'tpad +{gap:.1f}s last frame',
        )
    else:
        # No gap, use as-is
        Path(BG_NOAUDIO).rename(BG_PADDED)
        print(f'  No padding needed (gap {gap:.3f}s < 0.1s)')

    padded_dur = get_duration(BG_PADDED)
    print(f'  padded video: {padded_dur:.3f}s')

    # ── Step C: convert SRT → landscape ASS ──────────────────────────────────
    print('\nStep C — convert narration.srt → landscape ASS...')
    srt_to_ass(NARR_SRT, NARR_ASS)

    # ── Step D: overlay narration.mp3 + burn subtitles ───────────────────────
    print('\nStep D — overlay narration.mp3 + burn subtitles...')
    abs_ass = os.path.abspath(NARR_ASS).replace(':', '\\:')

    run(
        ['ffmpeg', '-y',
         '-i', BG_PADDED,
         '-i', NARR_MP3,
         '-vf', f"ass='{abs_ass}'",
         '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
         '-c:a', 'aac', '-b:a', '128k',
         '-shortest',
         FINAL],
        'FFmpeg assemble final',
    )

    # ── Result ────────────────────────────────────────────────────────────────
    final_dur  = get_duration(FINAL)
    final_size = get_size(FINAL)
    mins = int(final_dur // 60)
    secs = final_dur % 60

    print()
    print('=' * 54)
    print(f'  輸出：{FINAL}')
    print(f'  總時長：{mins}分{secs:.1f}秒（{final_dur:.1f}s）')
    print(f'  檔案大小：{final_size / 1024 / 1024:.1f} MB')
    print('=' * 54)

    # Cleanup intermediates
    for p in [LIST_TXT, BG_NOAUDIO, BG_PADDED, NARR_ASS]:
        try:
            os.unlink(p)
        except FileNotFoundError:
            pass
    print('  中間檔案已清理')


if __name__ == '__main__':
    main()
