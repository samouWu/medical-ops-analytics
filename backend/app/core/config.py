from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("MEDICAL_DATA_DIR", str(BASE_DIR / "data")))
DB_PATH = Path(os.getenv("MEDICAL_DB_PATH", str(DATA_DIR / "derived" / "medical_ops.db")))
SECRET_KEY = os.getenv("MEDICAL_SECRET_KEY", "dev-only-change-me")
TOKEN_MINUTES = int(os.getenv("MEDICAL_TOKEN_MINUTES", "480"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").lower()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
