import jwt
import time
import requests
from dotenv import load_dotenv
import os

load_dotenv("config/.env")

api_key = os.getenv("KLING_API_KEY")
api_secret = os.getenv("KLING_API_SECRET")

def get_token():
    now = int(time.time())
    payload = {
        "iss": api_key,
        "exp": now + 1800,
        "nbf": now - 5
    }
    return jwt.encode(payload, api_secret, algorithm="HS256")

token = get_token()
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.get("https://api.klingai.com/v1/account/costs", headers=headers)
print("狀態碼：", response.status_code)
print("回應：", response.json())
print("\nKling AI API 測試成功！")

# SpaceX IPO 影片生成提示詞（整合進主流程後使用）
KLING_VIDEO_PROMPT = (
    "SpaceX Falcon 9 rocket launching into space, "
    "dramatic cinematic shot, fire and smoke, "
    "night launch, ultra realistic"
)
