import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# ── Instagram ─────────────────────────────────────────────────────────────────
INSTAGRAM_PROFILE = "lelele_godoy"
POST_KEYWORD      = "agenda de forró"

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── Google Calendar ───────────────────────────────────────────────────────────
CALENDAR_NAME = "🎵 Forró DF"
TZ            = "America/Sao_Paulo"
SCOPES        = ["https://www.googleapis.com/auth/calendar"]

# ── Paths ─────────────────────────────────────────────────────────────────────
CREDENTIALS_FILE  = BASE_DIR / "google_credentials.json"
TOKEN_FILE        = BASE_DIR / "token.json"
IG_SESSION_FILE   = BASE_DIR / "instagram_session"
CALENDAR_ID_FILE  = BASE_DIR / "data" / "calendar_id.txt"

PROCESSED_FILE = BASE_DIR / "data" / "processed_posts.json"
TEMP_DIR       = BASE_DIR / "data" / "temp_images"
OUTPUT_DIR     = BASE_DIR / "output"
LOGS_DIR       = BASE_DIR / "logs"
