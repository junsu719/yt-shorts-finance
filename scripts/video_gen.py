import hashlib
import os
import re
import subprocess
import tempfile
import requests
from dotenv import load_dotenv

_MAX_CLIP_SECONDS = 25
_MIN_MOTION_BITRATE = 300_000  # bps — below this threshold the clip is treated as static

load_dotenv("config/.env")

_PEXELS_KEY   = os.getenv("PEXELS_API_KEY")
_PIXABAY_KEY  = os.getenv("PIXABAY_API_KEY")
_VECTEEZY_KEY = os.getenv("VECTEEZY_API_KEY")

_FALLBACK_QUERIES = [
    "stock market trading",
    "financial chart data",
    "semiconductor chip technology",
    "business stock exchange",
    "technology trading screen",
]

# Tags / URL fragments that indicate off-topic content for a tech/finance channel.
# Checked against Pixabay tags (comma-separated string) and Pexels video URL slugs.
_BLOCKED_KEYWORDS: set[str] = {
    # Industrial / metalwork
    "grinder", "grinding", "welding", "weld", "sparks", "metal cutting",
    "angle grinder", "metalwork", "forge", "foundry", "machining", "lathe",
    "drill press", "fabrication", "sawmill", "lumber",
    # Agriculture / food / animals
    "farm", "farming", "agriculture", "harvest", "crop", "livestock",
    "animal", "cow", "pig", "chicken", "sheep", "horse", "tractor",
    "cooking", "food", "kitchen", "restaurant", "chef", "baking",
    # Sports / outdoor / leisure
    "sport", "sports", "soccer", "football", "basketball", "tennis",
    "swimming", "running", "hiking", "mountain", "outdoor", "surf",
    "gym", "workout", "fitness", "yoga", "cycling", "skiing",
    # Nature / travel / lifestyle
    "nature", "landscape", "beach", "ocean", "forest", "flower",
    "travel", "tourism", "vacation", "wedding", "birthday", "party",
}


def _is_off_topic(tags: str, url: str = "") -> bool:
    """Return True if the clip is clearly off-topic for a tech/finance channel."""
    text = (tags + " " + url).lower()
    return any(kw in text for kw in _BLOCKED_KEYWORDS)


# ── Pexels ────────────────────────────────────────────────────────────────────

def _pexels_search(query: str, seen_ids: set) -> str | None:
    if not _PEXELS_KEY:
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": _PEXELS_KEY},
            params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 15},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception:
        return None

    for video in resp.json().get("videos", []):
        vid_id = f"pexels_{video['id']}"
        if vid_id in seen_ids:
            continue
        url_slug = video.get("url", "")
        if _is_off_topic("", url_slug):
            seen_ids.add(vid_id)
            print(f"[video] Pexels #{video['id']} 主題不符，跳過（{url_slug[-60:]}）")
            continue
        seen_ids.add(vid_id)
        return _pexels_best_url(video)
    return None


def _pexels_best_url(video: dict) -> str:
    files = video.get("video_files", [])
    portrait = [f for f in files if f.get("height", 0) > f.get("width", 0)]
    pool = portrait if portrait else files
    return sorted(pool, key=lambda f: f.get("height", 0), reverse=True)[0]["link"]


# ── Pixabay ───────────────────────────────────────────────────────────────────

def _pixabay_search(query: str, seen_ids: set) -> str | None:
    if not _PIXABAY_KEY:
        return None
    try:
        resp = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": _PIXABAY_KEY,
                "q": query,
                "video_type": "all",
                "orientation": "vertical",
                "per_page": 15,
            },
            timeout=10,
        )
        resp.raise_for_status()
    except Exception:
        return None

    for hit in resp.json().get("hits", []):
        vid_id = f"pixabay_{hit['id']}"
        if vid_id in seen_ids:
            continue
        tags = hit.get("tags", "")
        if _is_off_topic(tags):
            seen_ids.add(vid_id)
            print(f"[video] Pixabay #{hit['id']} 主題不符，跳過（tags: {tags[:60]}）")
            continue
        seen_ids.add(vid_id)
        return _pixabay_best_url(hit)
    return None


def _pixabay_best_url(video: dict) -> str:
    sizes = video.get("videos", {})
    for key in ("large", "medium", "small", "tiny"):
        url = sizes.get(key, {}).get("url", "")
        if url:
            return url
    raise RuntimeError("Pixabay video has no downloadable URL")


# ── Mixkit (scraper) ──────────────────────────────────────────────────────────

def _mixkit_search(query: str, seen_ids: set) -> str | None:
    """Scrape Mixkit search page for a free stock video URL."""
    slug = query.strip().replace(" ", "-").lower()
    url  = f"https://mixkit.co/free-stock-video/{slug}/"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        if resp.status_code != 200:
            return None
        html = resp.text
    except Exception:
        return None

    # Extract CDN video URLs embedded in the HTML
    # Mixkit embeds preview mp4 links in data attributes or script tags
    patterns = [
        r'https://assets\.mixkit\.co/[^"\']+\.mp4',
        r'https://cdn\.mixkit\.co/[^"\']+\.mp4',
    ]
    found = []
    for pat in patterns:
        found.extend(re.findall(pat, html))

    if not found:
        print(f"[Mixkit] WARNING: 0 mp4 URLs found for '{query}' — CDN pattern may need updating")

    for video_url in found:
        vid_id = f"mixkit_{hash(video_url)}"
        if vid_id not in seen_ids:
            seen_ids.add(vid_id)
            return video_url
    return None


# ── Vecteezy ──────────────────────────────────────────────────────────────────

def _vecteezy_search(query: str, seen_ids: set) -> str | None:
    """Search Vecteezy REST API for a free stock video."""
    if not _VECTEEZY_KEY:
        return None
    try:
        resp = requests.get(
            "https://api.vecteezy.com/v1/resources",
            headers={"Authorization": f"Bearer {_VECTEEZY_KEY}"},
            params={
                "query": query,
                "content_type": "video",
                "orientation": "portrait",
                "per_page": 15,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    for item in data.get("data", []):
        vid_id = f"vecteezy_{item.get('id', '')}"
        if vid_id not in seen_ids:
            video_url = (
                item.get("preview_url")
                or item.get("download_url")
                or item.get("url")
            )
            if video_url:
                seen_ids.add(vid_id)
                return video_url
    return None


# ── URL resolution ────────────────────────────────────────────────────────────

def _resolve_url(query: str, source: str, seen_ids: set) -> str | None:
    if source == "pexels":
        return _pexels_search(query, seen_ids)
    if source == "pixabay":
        return _pixabay_search(query, seen_ids) or _pexels_search(query, seen_ids)
    if source == "mixkit":
        return _mixkit_search(query, seen_ids) or _pexels_search(query, seen_ids)
    if source == "vecteezy":
        return _vecteezy_search(query, seen_ids) or _pexels_search(query, seen_ids)
    # auto: cycle all four sources
    return (
        _pexels_search(query, seen_ids)
        or _pixabay_search(query, seen_ids)
        or _mixkit_search(query, seen_ids)
        or _vecteezy_search(query, seen_ids)
    )


# ── Motion validation ─────────────────────────────────────────────────────────

def _encoded_bitrate(path: str) -> int:
    """Return the video stream bitrate (bps) of an already-encoded clip, or 0 on error."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", "-select_streams", "v:0", path,
            ],
            capture_output=True, text=True, check=True,
        )
        import json
        streams = json.loads(result.stdout).get("streams", [])
        if not streams:
            return 0
        return int(streams[0].get("bit_rate", 0))
    except Exception:
        return 0


def _file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _encode_clip(url: str, output_path: str, seen_hashes: set[str] | None = None) -> bool:
    """Download url, encode to output_path, return True if clip is valid and unique.

    Rejects static clips (bitrate < _MIN_MOTION_BITRATE) and content duplicates
    (MD5 already in seen_hashes). On rejection the output file is removed.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        subprocess.run(
            [
                "ffmpeg", "-y", "-i", tmp_path,
                "-t", str(_MAX_CLIP_SECONDS),
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-r", "30", "-pix_fmt", "yuv420p", "-an",
                output_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        bitrate = _encoded_bitrate(output_path)
        if bitrate < _MIN_MOTION_BITRATE:
            print(f"[video] 靜態素材拒絕（bitrate={bitrate//1000}kbps < {_MIN_MOTION_BITRATE//1000}kbps），嘗試下一個")
            os.remove(output_path)
            return False

        if seen_hashes is not None:
            md5 = _file_md5(output_path)
            if md5 in seen_hashes:
                print(f"[video] 重複素材拒絕（MD5={md5[:8]}…），嘗試下一個")
                os.remove(output_path)
                return False
            seen_hashes.add(md5)

        return True
    except Exception:
        return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── Public API ────────────────────────────────────────────────────────────────

SOURCES = ["pexels", "pixabay", "mixkit", "vecteezy"]

_MAX_ATTEMPTS = 5  # per source: try up to this many distinct URLs before giving up


def fetch_clip(
    query: str,
    output_path: str,
    source: str = "auto",
    seen_ids: set | None = None,
    seen_hashes: set[str] | None = None,
):
    """Download a unique portrait video clip to output_path.

    source: "pexels" | "pixabay" | "mixkit" | "vecteezy" | "auto"
    seen_ids:     shared set of API video IDs already used; prevents same ID twice.
    seen_hashes:  shared set of MD5 hashes of encoded clips; prevents same content twice.
                  Pass the same set across all fetch_clip calls in a session.
    """
    if seen_ids is None:
        seen_ids = set()

    # Try primary source up to _MAX_ATTEMPTS times (seen_ids prevents repeats)
    for _ in range(_MAX_ATTEMPTS):
        url = _resolve_url(query, source, seen_ids)
        if url is None:
            break
        if _encode_clip(url, output_path, seen_hashes):
            return

    # Fallback to generic queries across all sources
    for fallback in _FALLBACK_QUERIES:
        for _ in range(_MAX_ATTEMPTS):
            url = _resolve_url(fallback, "auto", seen_ids)
            if url is None:
                break
            print(f"[video] '{query}' 無動態素材，改用 fallback: '{fallback}'")
            if _encode_clip(url, output_path, seen_hashes):
                return

    raise RuntimeError(f"找不到合適的動態影片素材（query='{query}'）")
