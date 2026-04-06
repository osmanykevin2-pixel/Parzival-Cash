import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
APP_BASE_URL = os.getenv("APP_BASE_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")