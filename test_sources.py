"""素材庫多樣性測試：測試四個來源各指定關鍵字，回報成功/失敗與是否重複。"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv("config/.env")

from scripts.video_gen import fetch_clip

TEST_CASES = [
    ("pixabay", "stock market bull"),
    ("pixabay", "AI server data center"),
    ("pixabay", "semiconductor chip technology"),
    ("pexels",  "stock market growth"),
    ("pexels",  "financial technology"),
    ("pexels",  "server room"),
    ("mixkit",  "stock market"),
    ("mixkit",  "technology business"),
    ("mixkit",  "data visualization"),
    ("vecteezy","financial chart"),
    ("vecteezy","technology background"),
    ("vecteezy","business growth"),
]

results = {"pixabay": [], "pexels": [], "mixkit": [], "vecteezy": []}
seen_ids = set()

with tempfile.TemporaryDirectory() as tmpdir:
    for i, (source, query) in enumerate(TEST_CASES):
        out = os.path.join(tmpdir, f"test_{i:02d}.mp4")
        try:
            fetch_clip(query, out, source=source, seen_ids=seen_ids)
            ok = os.path.exists(out) and os.path.getsize(out) > 1000
            results[source].append(("OK" if ok else "EMPTY", query))
        except Exception as e:
            results[source].append(("FAIL", f"{query} ({e})"))

print("\n======== 素材庫測試報告 ========")
total_ok = 0
for src, items in results.items():
    ok_count = sum(1 for s, _ in items if s == "OK")
    total_ok += ok_count
    print(f"\n[{src.upper()}] {ok_count}/{len(items)} 成功")
    for status, q in items:
        mark = "✓" if status == "OK" else "✗"
        print(f"  {mark} {q}")

print(f"\n重複素材數：{len([i for i in seen_ids if True]) - total_ok} 個被 seen_ids 過濾")
print(f"總計唯一素材：{total_ok}/{len(TEST_CASES)}")
