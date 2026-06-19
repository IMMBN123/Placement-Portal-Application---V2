from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm import aliased
from app.models import db, user, company, student, placement_drive, application
from app.utils import role_required
from datetime import datetime

student_bp = Blueprint('student', __name__, url_prefix='/api/student')

student_cgpa = student.query.filter(current_user.id == student.user_id).with_entities(student.cgpa).scalar()

@student_bp.route('/dashboard', methods=['GET'])
@login_required
@role_required('student')
def get_stats():
    total_app_count = student.query.join(application).filter(current_user.id == student.user_id).count()
    shortlisted_app_count = student.query.join(application).filter(current_user.id == student.user_id, application.status == 'Shortlisted').count()
    accepted_app_count = student.query.join(application).filter(current_user.id == student.user_id, application.status == 'Accepted').count()
    rejected_app_count = student.query.join(application).filter(current_user.id == student.user_id, application.status == 'Rejected').count()
    ongoing_drive_count = placement_drive.query.join(company).join(user).filter(placement_drive.is_active == True, company.is_approved == True, user.is_active == True).count()
    eligible_drive_count = placement_drive.query.join(company).join(user).filter(placement_drive.is_active == True, company.is_approved == True, user.is_active == True, placement_drive.min_cgpa <= student_cgpa).count()

    return jsonify({"total_applications":[a.to_dict() for a in total_app_count],
                    "shortisted_applications":[a.to_dict() for a in shortlisted_app_count],
                    "accepted_applications":[a.to_dict() for a in accepted_app_count],
                    "rejected_applications":[a.to_dict() for a in rejected_app_count],
                    'ongoing_drives':[d.to_dict() for d in ongoing_drive_count],
                    'eligible_drives':[d.to_dict() for d in eligible_drive_count]}), 200

@student_bp.route('/glance/drives', methods=['GET'])
@login_required
@role_required('student')
def get_five_drives():
    eligible_drives = placement_drive.query.join(company).join(user).filter(placement_drive.is_active == True, company.is_approved == True, user.is_active == True, placement_drive.min_cgpa <= student_cgpa).limit(5).all()
    return jsonify({"eligible_drives": [d.to_dict() for d in eligible_drives]}), 200

@student_bp.route('/glance/applications', methods=['GET'])
@login_required
@role_required('student')
def get_five_applications():
    applications = student.query.join(application).filter(current_user.id == student.user_id).limit(5).all()
    return jsonify({"recent_applications": [a.to_dict() for a in applications]}), 200

