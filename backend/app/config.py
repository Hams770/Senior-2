"""Settings read from environment variables (see .env.example)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    """Read KEY=value lines from backend/.env (never committed); real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'hiremind.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "120"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
MAX_CV_BYTES = 10 * 1024 * 1024  # FR-05: at most 10 MB
ALLOWED_CV_TYPES = {".pdf": b"%PDF", ".docx": b"PK\x03\x04"}  # D5: PDF and DOCX only
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# Fit classifier (FR-09). Needs requirements-model.txt; the first run downloads the pinned tokenizer (~1 MB).
MODEL_DIR = BASE_DIR / "models"
FIT_ENABLED = os.getenv("FIT_MODEL", "on").lower() != "off"
FIT_WEIGHTS = Path(os.environ["FIT_WEIGHTS"]) if os.getenv("FIT_WEIGHTS") else None  # default: models/<card file>

# Feedback drafts (FR-17). Without a key the drafts come from a fixed template.
LLM_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
LLM_WORKSPACE_ID = os.getenv("ANTHROPIC_WORKSPACE_ID", "")  # only for keys not scoped to a workspace
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "30"))
