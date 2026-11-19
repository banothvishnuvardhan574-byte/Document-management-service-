from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

APP_NAME = os.getenv("APP_NAME", "Document Management Service")
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(BASE_DIR / 'documents.db').resolve()}"
)
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))).resolve()
MAX_FILE_SIZE_MB = max(1, int(os.getenv("MAX_FILE_SIZE_MB", "10")))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ext.strip().lower()
    for ext in os.getenv("ALLOWED_EXTENSIONS", ".pdf,.doc,.docx,.txt,.rtf").split(",")
    if ext.strip()
}
VALID_STATUSES = ["RECEIVED", "PROCESSING", "AVAILABLE", "ARCHIVED", "FAILED"]
VALID_STATUS_TRANSITIONS = {
    "RECEIVED": {"PROCESSING"},
    "PROCESSING": {"AVAILABLE", "FAILED"},
    "AVAILABLE": {"ARCHIVED"},
    "ARCHIVED": set(),
    "FAILED": set(),
}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
