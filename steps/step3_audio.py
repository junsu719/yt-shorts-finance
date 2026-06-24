"""Step 3：生成配音（edge-tts，支援繁體中文 zh-TW-HsiaoChenNeural）"""

import asyncio
from pathlib import Path

BASE_DIR  = Path(__file__).parent.parent
AUDIO_DIR = BASE_DIR / "audio"

VOICE = "zh-TW-HsiaoChenNeural"
SEGMENT_SECONDS = {1: 20, 2: 30, 3: 30, 4: 30, 5: 40, 6: 40, 7: 20}


def generate_audio(config: dict) -> dict:
    script_text: str = config.get("script", {}).get("text", "")
    note = config.get("audio_note", "")
    if note:
        print(f"[配音] 套用修改意見：{note}")

    lines = [l for l in script_text.splitlines()
             if l.strip() and not l.startswith("【")]
    clean_text = " ".join(lines)

    output_path = AUDIO_DIR / "narration.mp3"

    try:
        import edge_tts
        asyncio.run(_synthesize(clean_text, output_path))
        method = "edge-tts"
    except ImportError:
        print("  [警告] edge-tts 未安裝，跳過實際合成。")
        print("  安裝指令：pip install edge-tts")
        output_path = None
        method = "（未生成，需安裝 edge-tts）"

    return {
        "path":              output_path,
        "estimated_seconds": sum(SEGMENT_SECONDS.values()),
        "method":            method,
        "voice":             VOICE,
        "segments":          SEGMENT_SECONDS,
    }


async def _synthesize(text: str, path: Path):
    import edge_tts
    comm = edge_tts.Communicate(text, VOICE, rate="+0%", pitch="+0Hz")
    await comm.save(str(path))
