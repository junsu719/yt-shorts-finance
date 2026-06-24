"""Step 5：上傳至 YouTube（YouTube Data API v3）"""

from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
CREDENTIALS = BASE_DIR / "config" / "client_secret.json"   # 對齊既有專案路徑
TOKEN_FILE  = BASE_DIR / "config" / "token.json"


def upload_youtube(config: dict) -> str:
    note = config.get("upload_note", "")
    if note:
        print(f"[上傳] 套用修改意見：{note}")

    video_path = config.get("video", {}).get("path")
    meta       = config.get("youtube_meta", {})

    if not CREDENTIALS.exists():
        print("  [警告] 未找到 YouTube API 憑證。")
        print(f"  預期路徑：{CREDENTIALS}")
        return "（未上傳）"

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds   = _get_credentials()
        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title":       meta.get("title", ""),
                "description": meta.get("description", ""),
                "tags":        meta.get("tags", []),
                "categoryId":  "27",
            },
            "status": {"privacyStatus": meta.get("privacy", "private")},
        }
        media    = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        response = youtube.videos().insert(
            part="snippet,status", body=body, media_body=media).execute()

        return f"https://www.youtube.com/watch?v={response.get('id', '')}"

    except ImportError:
        print("  [警告] 缺少套件。安裝：pip install google-api-python-client google-auth-oauthlib")
        return "（未上傳）"


def _get_credentials():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds  = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow  = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return creds
