from functools import wraps
from flask_login import current_user
from flask import abort
from .models import db, placement_drive
from datetime import date

def role_required(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)

            # Admin can access everything
            if current_user.role == "admin":
                return func(*args, **kwargs)

            if current_user.role != role:
                abort(403)

            return func(*args, **kwargs)

        return wrapper
    return decorator

def auto_close_expired_drives():
    expired_drives = placement_drive.query.filter(
        placement_drive.deadline < date.today(),
        placement_drive.is_active == True
    ).all()

    for drive in expired_drives:
        drive.is_active = False

    db.session.commit()

