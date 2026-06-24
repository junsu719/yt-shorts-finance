from scripts.video_gen import fetch_clip
from pathlib import Path

Path("output/test").mkdir(parents=True, exist_ok=True)

print("搜尋並下載影片...")
fetch_clip("stock market trading charts finance", "output/test/clip_test.mp4")
print("完成：output/test/clip_test.mp4")
