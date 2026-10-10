import os
from datetime import timedelta


class Config:
    # ── Core ──────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production-use-a-long-random-string")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///mediwallet.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── File uploads ──────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(os.path.dirname(__file__), "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024          # 16 MB hard limit (Flask enforces 413)
    ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}

    # ── Session ───────────────────────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # ── Sharing ───────────────────────────────────────────────────────────────
    DEFAULT_SHARE_EXPIRY_HOURS = 24
    MAX_SHARE_EXPIRY_HOURS = 720                    # 30 days
    # Public base URL used for QR code generation and shared links.
    # Defaults to empty string, which dynamically resolves from incoming request or LAN IP.
    # Set APP_BASE_URL (or PUBLIC_BASE_URL) in environment (e.g. http://10.99.9.11:5000 or https://yourdomain.com)
    PUBLIC_BASE_URL = os.environ.get("APP_BASE_URL") or os.environ.get("PUBLIC_BASE_URL", "")

    # ── OCR (Tesseract) ───────────────────────────────────────────────────────
    # Override with env var if Tesseract is installed in a non-default path
    TESSERACT_CMD = os.environ.get(
        "TESSERACT_CMD",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Windows default
    )


class TestingConfig(Config):
    """Used by pytest fixtures."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    # Use a temp dir per-test (override in fixture)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "test_uploads")
