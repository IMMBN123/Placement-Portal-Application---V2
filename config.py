import os
from dotenv import load_dotenv
from celery.schedules import crontab
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

    CELERY = {
        "broker_url": "redis://localhost:6379/0",
        "result_backend": "redis://localhost:6379/0",
        "task_ignore_result": False,
        "timezone": "Asia/Kolkata",
        "enable_utc": False,         
        "imports": ("app.tasks",),
        
        "beat_schedule": {
            # JOB A: Runs every single day at 9:00 AM
            "daily-deadline-reminders": {
                "task": "send_daily_deadline_reminders",
                "schedule": crontab(hour=9, minute=0),
            },
            
            # JOB B: Runs only on the 1st day of every month at 9:00 AM
            "monthly-activity-report": {
                "task": "send_monthly_admin_report",
                "schedule": crontab(month_of_year=1, hour=9, minute=0),
            },

            # JOB C: Runs every single day at 9:00 AM
            "daily-interview-reminders": {
                "task": "send_daily_interview_reminders",
                "schedule": crontab(hour=9, minute=0),
            },

            "monthly-company-report": {
                "task": "send_monthly_company_report",
                "schedule": crontab(month_of_year=1, hour=9, minute=0),
            },

        }
    }

    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = "redis://localhost:6379/1"
    CACHE_DEFAULT_TIMEOUT = 300