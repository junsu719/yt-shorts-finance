from scripts.tts import synthesize

duration = synthesize(
    "台積電上季淨利創歷史新高，年增幅達三成八，AI 晶片需求持續爆發！",
    "assets/audio/test_output.mp3"
)
print(f"語音合成完成，時長：{duration:.1f}s → assets/audio/test_output.mp3")
