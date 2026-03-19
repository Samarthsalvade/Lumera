import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY     = os.environ.get('SECRET_KEY',     'lumera-super-secret-key-min-32-chars-long-12345')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'lumera-super-secret-key-min-32-chars-long-12345')

    # ── Database ──────────────────────────────────────────────────────────────
    # Uses Neon PostgreSQL in production, falls back to SQLite locally
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///lumera.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Cloudinary ────────────────────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY    = os.environ.get('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '')

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)

    # ── Uploads ───────────────────────────────────────────────────────────────
    UPLOAD_FOLDER      = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}