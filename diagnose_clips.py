#!/usr/bin/env python3
import json, subprocess, sys
sys.path.insert(0, '/home/junsu/yt-shorts-finance')
from scripts.slot_allocator import build_slot_plan

BASE     = '/mnt/d/yt-shorts-finance/output/risk_education_segments'
SRT      = f'{BASE}/narration.srt'
CHARTS   = f'{BASE}/narration_charts.json'
NARR_MP3 = f'{BASE}/narration.mp3'

script    = json.loads(open(f'{BASE}/script.json').read())
slot_plan = build_slot_plan(SRT, CHARTS, script.get('search_queries', []), 'education')

def dur(path):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1', path],
        capture_output=True, text=True)
    return float(r.stdout.strip().split('=')[1])

narr_dur = dur(NARR_MP3)
print(f'narration.mp3 total: {narr_dur:.3f}s')
print()
print(f"{'Slot':<8} {'Expected':>10} {'Actual':>10} {'Deficit':>9}")
print('-' * 44)

total_exp = 0.0
total_act = 0.0
for spec in slot_plan:
    f       = f'{BASE}/clip_{spec.index:02d}.mp4'
    actual  = dur(f)
    deficit = spec.duration - actual
    flag    = '  <- SHORT' if deficit > 0.5 else ''
    print(f"clip_{spec.index:02d}   {spec.duration:>10.3f} {actual:>10.3f} {deficit:>+9.3f}{flag}")
    total_exp += spec.duration
    total_act += actual

print('-' * 44)
print(f"TOTAL    {total_exp:>10.3f} {total_act:>10.3f} {total_exp-total_act:>+9.3f}")
print()
print(f"narration.mp3:          {narr_dur:.3f}s")
print(f"total video (all clips): {total_act:.3f}s")
print(f"gap narration - video:  {narr_dur - total_act:+.3f}s")
