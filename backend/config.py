'''import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'lumera-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///lumera.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}'''
    
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


class Config:
    SECRET_KEY     = os.environ.get('SECRET_KEY',     'lumera-super-secret-key-min-32-chars-long-12345')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'lumera-super-secret-key-min-32-chars-long-12345')

    SQLALCHEMY_DATABASE_URI        = 'sqlite:///lumera.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)

    UPLOAD_FOLDER      = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}