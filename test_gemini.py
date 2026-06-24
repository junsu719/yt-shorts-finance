import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv("config/.env")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content("用繁體中文說一句話介紹蘋果公司的最新財報重點")
print(response.text)
print("\nGemini API 測試成功！")
