import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Better to put uploads in static folder for Vue/CDN access
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads") 
ALLOWED_EXTENSIONS = ["doc", "docx", "pdf", "png", "jpg", "jpeg", "webp"]
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

class Config:
    # Basic Flask Config
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-if-env-is-missing")
    
    # SQLAlchemy Config (Keeping your mad2.db name!)
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "mad2.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload Config
    UPLOAD_FOLDER = UPLOAD_FOLDER
    ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH

    # Celery & Redis Config for V2 Background Jobs
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'