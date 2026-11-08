"""Settings read from environment variables (see .env.example)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'hiremind.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "120"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
MAX_CV_BYTES = 10 * 1024 * 1024  # FR-05: at most 10 MB
ALLOWED_CV_TYPES = {".pdf": b"%PDF", ".docx": b"PK\x03\x04"}  # D5: PDF and DOCX only
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# Feedback drafts (FR-17). Without a key the drafts come from a fixed template.
LLM_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "30"))
