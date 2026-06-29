"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/jobs.db")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@vaughanashe.ai")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")

SCRAPE_HEADLESS = os.getenv("SCRAPE_HEADLESS", "true").lower() == "true"
SCRAPE_MAX_RESULTS = int(os.getenv("SCRAPE_MAX_RESULTS", "100"))

# OAuth2
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")

