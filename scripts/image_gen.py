import os
import subprocess
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv("config/.env")
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

_CLIP_DURATION = 4   # seconds each image clip plays
_ZOOM_SPEED = 0.0008  # gentle Ken Burns zoom-in speed per frame


def generate_image(prompt: str, output_path: str) -> str:
    """Generate a 9:16 image via Imagen 3 and save raw bytes to output_path."""
    result = _client.models.generate_images(
        model="imagen-4.0-generate-001",
        prompt=(
            f"{prompt}, "
            "vertical 9:16 composition, photorealistic, cinematic lighting, "
            "no text overlay, no watermarks, no human faces"
        ),
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="9:16",
            safety_filter_level="BLOCK_LOW_AND_ABOVE",
            person_generation="DONT_ALLOW",
        ),
    )
    if not result.generated_images:
        raise RuntimeError("Imagen API 未回傳任何圖像")

    with open(output_path, "wb") as f:
        f.write(result.generated_images[0].image.image_bytes)
    return output_path


def image_to_clip(image_path: str, output_path: str, duration: int = _CLIP_DURATION):
    """Convert a still image to a video clip with a gentle Ken Burns zoom-in."""
    frames = duration * 30
    zoom_expr = f"min(zoom+{_ZOOM_SPEED},1.3)"

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                f"zoompan=z='{zoom_expr}':d={frames}"
                ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920,"
                "fps=30"
            ),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-an",
            output_path,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
