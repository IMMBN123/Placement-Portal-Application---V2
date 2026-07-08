from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm import aliased
from app import cache
from app.models import db, user, company, student, placement_drive, application
from app.utils import role_required
from datetime import datetime
from app.tasks import export_student_applications_csv
from celery.result import AsyncResult
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
import uuid
import os
import hashlib

student_bp = Blueprint('student', __name__, url_prefix='/api/student')

def get_student_cgpa():
    student_cgpa = student.query.filter(current_user.id == student.user_id).with_entities(student.cgpa).scalar()
    return student_cgpa

def get_applied_drive_ids():
    applied_drive_ids = db.session.query(application.placement_drive_id).filter(
    application.student_id == current_user.id)
    return applied_drive_ids

@student_bp.route('/dashboard', methods=['GET'])
@login_required
@role_required('student')
def get_stats():
    student_cgpa = get_student_cgpa()
    total_app_count = student.query.join(application).filter(current_user.id == student.user_id).count()
    shortlisted_app_count = student.query.join(application).filter(current_user.id == student.user_id, application.status == 'Shortlisted').count()
    accepted_app_count = student.query.join(application).filter(current_user.id == student.user_id, application.status == 'Accepted').count()
    rejected_app_count = student.query.join(application).filter(current_user.id == student.user_id, application.status == 'Rejected').count()
    ongoing_drive_count = placement_drive.query.join(company).join(user).filter(placement_drive.is_active == True, company.is_approved == True, user.is_active == True).count()
    eligible_drive_count = placement_drive.query.join(company).join(user).filter(placement_drive.is_active == True, company.is_approved == True, user.is_active == True, placement_drive.min_cgpa <= student_cgpa).count()
    applied_drive_count = placement_drive.query.join(application).join(company).join(user).filter(placement_drive.is_approved == True,placement_drive.is_active == True,application.student_id == current_user.id,user.is_active == True).count()

    return jsonify({"total_applications": total_app_count,
                    "shortisted_applications": shortlisted_app_count,
                    "accepted_applications": accepted_app_count,
                    "rejected_applications": rejected_app_count,
                    'ongoing_drives': ongoing_drive_count,
                    'eligible_drives': eligible_drive_count,
                    'applied_drives': applied_drive_count}), 200

@student_bp.route('/glance/drives', methods=['GET'])
@login_required
@role_required('student')
def get_five_drives():
    student_cgpa = get_student_cgpa()
    applied_drive_ids = get_applied_drive_ids()
    eligible_drives = placement_drive.query.join(company).join(user).filter(
        placement_drive.is_active == True,
        company.is_approved == True,
        user.is_active == True, 
        placement_drive.min_cgpa <= student_cgpa,
        ~placement_drive.id.in_(applied_drive_ids)).limit(5).all()
    return jsonify({"eligible_drives": [d.to_dict() for d in eligible_drives]}), 200

@student_bp.route('/glance/applications', methods=['GET'])
@login_required
@role_required('student')
def get_five_applications():
    results = db.session.query(
        placement_drive,         
        application.status,       
        application.applied_at,
        application.remarks    
    ).join(
        application, 
        placement_drive.id == application.placement_drive_id
    ).filter(
        application.student_id == current_user.id
    ).limit(5).all()
    
    summary_data = []
    
    for drive, app_status, app_applied_at, app_remarks in results:
        drive_data = drive.to_dict()
        
        drive_data["status"] = app_status
        drive_data["applied_at"] = app_applied_at.isoformat() if app_applied_at else None
        drive_data["remarks"] = app_remarks
        
        summary_data.append(drive_data)

    return jsonify({"recent_applications": summary_data}), 200

@student_bp.route('/applications', methods=['GET'])
@login_required
@role_required('student')
def get_all_applications():
    active_results = db.session.query(
            placement_drive,
            application.id,
            application.status,
            application.applied_at,
            application.remarks
        ).select_from(application)\
         .join(placement_drive, application.placement_drive_id == placement_drive.id)\
         .join(company, placement_drive.company_id == company.user_id)\
         .join(user, company.user_id == user.id)\
         .filter(
             application.student_id == current_user.id,
             placement_drive.is_active == True,
             user.is_active == True,
             company.is_approved == True).all()

    active_applications_data = []
    for drive, app_id, app_status, app_applied_at, app_remarks in active_results:
        drive_data = drive.to_dict()
        drive_data["application_id"] = app_id
        drive_data["status"] = app_status
        drive_data["applied_at"] = app_applied_at.isoformat() if app_applied_at else None
        drive_data["remarks"] = app_remarks
        
        active_applications_data.append(drive_data)

    previous_results = db.session.query(
        placement_drive,
        application.id,
        application.status,
        application.applied_at,
        application.remarks
    ).select_from(application)\
        .join(placement_drive, application.placement_drive_id == placement_drive.id)\
        .join(company, placement_drive.company_id == company.user_id)\
        .join(user, company.user_id == user.id)\
        .filter(
            application.student_id == current_user.id,
            company.is_approved == True,
            placement_drive.is_active == False).all()

    prev_applications_data = []
    for drive, app_id, app_status, app_applied_at, app_remarks in previous_results:
        drive_data = drive.to_dict()
        
        drive_data["application_id"] = app_id
        drive_data["status"] = app_status
        drive_data["applied_at"] = app_applied_at.isoformat() if app_applied_at else None
        drive_data["remarks"] = app_remarks
        
        prev_applications_data.append(drive_data)

    return jsonify({"active_applications": active_applications_data,
                    "previous_applications": prev_applications_data })

@student_bp.route('/profile', methods=['GET'])
@login_required
@role_required('student')
def get_profile():
    print(current_user.id)
    profile = student.query.filter_by(user_id=current_user.id).first_or_404()
    return jsonify({'profile': profile.to_dict()}), 200

@student_bp.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    return jsonify({'error': 'File size too large'})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@student_bp.route('/profile/update', methods=['POST'])
@login_required
@role_required('student')
def update_profile():
    s = student.query.filter_by(user_id=current_user.id).first_or_404()
    if not s:
        return jsonify({"error": "Student profile not found"}), 404
    
    if not s.user.is_active:
        return jsonify({"error": "Invalid Action"}), 403
    
    data = request.form
    def get_field(key, default=""):
        val = data.get(key)
        return str(val).strip() if val is not None else default

    email = get_field('email')
    full_name = get_field('full_name')
    roll_number = get_field('roll_number')
    branch = get_field('branch')
    age = get_field('age')
    graduation_year = get_field('graduation_year')
    cgpa = get_field('cgpa')
    phone = get_field('phone')
    linkedin_url = get_field('linkedin_url')

    existing_user = user.query.filter(user.email == email, user.id != current_user.id).first()
    if existing_user:
        return jsonify({"error": "Email is already registered by another student/user"}), 409
            
    existing_student = student.query.filter(student.roll_number == roll_number, student.user_id != current_user.id).first()
    if existing_student:
        return jsonify({"error": "Roll Number is already assigned to another student"}), 409

    try:
        file = request.files.get('resume_link')
        resume_link = s.resume_link
        if file and file.filename:
            if not allowed_file(file.filename):
                return jsonify({"error": "Invalid file type. Allowed formats: PDF, Images (PNG, JPG, JPEG, WEBP)."}), 400

            new_file_bytes = file.read()
            new_file_hash = hashlib.sha256(new_file_bytes).hexdigest()
            file.seek(0)

            upload_folder = current_app.config['UPLOAD_FOLDER']
            old_file_path = None
            old_filename = None

            if os.path.exists(upload_folder):
                for fname in os.listdir(upload_folder):
                    if fname.startswith(roll_number):
                        old_filename = fname
                        old_file_path = os.path.join(upload_folder, fname)
                        break

            is_file_changed = True
            if old_file_path and os.path.exists(old_file_path):
                with open(old_file_path, 'rb') as f:
                    old_file_bytes = f.read()
                    old_file_hash = hashlib.sha256(old_file_bytes).hexdigest()

                if new_file_hash == old_file_hash:
                    is_file_changed = False
                    print(f"Duplicate file content detected for {roll_number}. Skipping file save.")
                    resume_link = old_filename

            if is_file_changed:
                if os.path.exists(upload_folder):
                    for fname in os.listdir(upload_folder):
                        if fname.startswith(roll_number):
                            try:
                                os.remove(os.path.join(upload_folder, fname))
                                print(f"Removed outdated physical match: {fname}")
                            except Exception as delete_error:
                                print(f"Error removing file from disk: {delete_error}")

                safe_name = secure_filename(file.filename)
                filename = f"{roll_number}_{uuid.uuid4().hex[:8]}_{safe_name}"
                file.save(os.path.join(upload_folder, filename))
                resume_link = filename

        s.user.email = email
        s.full_name = full_name
        s.roll_number = roll_number
        s.age = age
        s.phone = phone
        s.cgpa = cgpa
        s.branch = branch
        s.graduation_year = graduation_year
        s.linkedin_url = linkedin_url
        s.resume_link = resume_link

        db.session.commit()

        cache.delete('admin_all_stats')
        cache.delete('admin_five_students')
        cache.delete('admin_all_students')
        cache.delete('admin_five_drives')
        cache.delete('admin_all_drives')
        cache.delete('admin_five_applications')
        cache.delete('admin_all_applications')
        cache.delete('admin_all_search')

        return jsonify({"message": f"Profile for student '{full_name}' updated successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Student Update Failure Exception: {e}")
        return jsonify({"error": "An internal database error occurred while committing changes."}), 500

@student_bp.route('/search', methods=['GET'])
@login_required
@role_required('student')
def student_search():

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"error": "Type something in the search bar"}), 400

    search_term = f"%{query}%"

    applied_drives = placement_drive.query.join(application).join(company).join(user).filter(
        placement_drive.is_approved == True,
        placement_drive.is_active == True,
        application.student_id == current_user.id,
        user.is_active == True,
        or_(
            placement_drive.job_title.ilike(search_term),
            placement_drive.location.ilike(search_term),
            company.company_name.ilike(search_term)
        )
    ).all()

    cgpa = get_student_cgpa()
    applied_drive_ids = get_applied_drive_ids()
    eligible_drives = placement_drive.query.join(company).join(user).filter(
        placement_drive.is_approved == True,
        placement_drive.is_active == True,
        company.is_approved == True,
        user.is_active == True,
        placement_drive.min_cgpa <= cgpa,
        ~placement_drive.id.in_(applied_drive_ids),
        or_(
            placement_drive.job_title.ilike(search_term),
            placement_drive.location.ilike(search_term),
            company.company_name.ilike(search_term)
        )
    ).all()

    non_eligible_drives = placement_drive.query.join(company).join(user).filter(
        placement_drive.is_approved == True,
        placement_drive.is_active == True,
        company.is_approved == True,
        user.is_active == True,
        placement_drive.min_cgpa > cgpa,
        or_(
            placement_drive.job_title.ilike(search_term),
            placement_drive.location.ilike(search_term),
            company.company_name.ilike(search_term)
        )
    ).all()

    active_applications = db.session.query(
            placement_drive,
            application.id,
            application.status,
            application.applied_at,
            application.remarks
            ).select_from(application)\
            .join(placement_drive, application.placement_drive_id == placement_drive.id)\
            .join(company, placement_drive.company_id == company.user_id)\
            .join(user, company.user_id == user.id)\
            .filter(
                application.student_id == current_user.id,
                placement_drive.is_active == True,
                user.is_active == True,
                company.is_approved == True,
                or_(
                    placement_drive.job_title.ilike(search_term),
                    placement_drive.location.ilike(search_term),
                    company.company_name.ilike(search_term)
                )
            ).all()

    active_applications_data = []
    for drive, app_id, app_status, app_applied_at, app_remarks in active_applications:
        drive_data = drive.to_dict()
        
        drive_data["application_id"] = app_id
        drive_data["status"] = app_status
        drive_data["applied_at"] = app_applied_at.isoformat() if app_applied_at else None
        drive_data["remarks"] = app_remarks
        
        active_applications_data.append(drive_data)

    prev_applications = db.session.query(
        placement_drive,
        application.id,
        application.status,
        application.applied_at,
        application.remarks
    ).select_from(application)\
        .join(placement_drive, application.placement_drive_id == placement_drive.id)\
        .join(company, placement_drive.company_id == company.user_id)\
        .join(user, company.user_id == user.id)\
        .filter(
            application.student_id == current_user.id,
            company.is_approved == True,
            placement_drive.is_active == False,
            or_(
                placement_drive.job_title.ilike(search_term),
                placement_drive.location.ilike(search_term),
                company.company_name.ilike(search_term)
            )
        ).all()

    prev_applications_data = []
    for drive, app_id, app_status, app_applied_at, app_remarks in prev_applications:
        drive_data = drive.to_dict()
    
        drive_data["application_id"] = app_id
        drive_data["status"] = app_status
        drive_data["applied_at"] = app_applied_at.isoformat() if app_applied_at else None
        drive_data["remarks"] = app_remarks
        
        prev_applications_data.append(drive_data)
    
    if not applied_drives and not eligible_drives and not non_eligible_drives and not active_applications and not prev_applications:
        return jsonify({"error": "Search term has no match!"}), 404

    return jsonify({
        "non_eligible_drives": [d.to_dict() for d in non_eligible_drives],
        "applied_drives": [d.to_dict() for d in applied_drives],
        "eligible_drives": [d.to_dict() for d in eligible_drives],
        "active_applications": active_applications_data,
        "previous_applications": prev_applications_data,
    }), 200

@student_bp.route('/drives', methods=['GET'])
@login_required
@role_required('student')
def get_all_drives():
    applied_drives = placement_drive.query.join(application).join(company).join(user).filter(
        placement_drive.is_approved == True,
        placement_drive.is_active == True,
        application.student_id == current_user.id,
        user.is_active == True).all()

    cgpa = get_student_cgpa()
    applied_drive_ids = get_applied_drive_ids()
    eligible_drives = placement_drive.query.join(company).join(user).filter(
        placement_drive.is_approved == True,
        placement_drive.is_active == True,
        company.is_approved == True,
        user.is_active == True,
        placement_drive.min_cgpa <= cgpa,
        ~placement_drive.id.in_(applied_drive_ids)).all()

    
    non_eligible_drives = placement_drive.query.join(company).join(user).filter(
        placement_drive.is_approved == True,
        placement_drive.is_active == True,
        company.is_approved == True,
        user.is_active == True,
        placement_drive.min_cgpa > cgpa,
        ).all()
    
    return jsonify({
        "non_eligible_drives": [d.to_dict() for d in non_eligible_drives],
        "applied_drives": [d.to_dict() for d in applied_drives],
        "eligible_drives": [d.to_dict() for d in eligible_drives]}), 200

@student_bp.route('/drives/<int:drive_id>/apply', methods=['POST'])
@login_required
@role_required('student')
def apply(drive_id):

    current_student = student.query.filter_by(user_id=current_user.id).first_or_404()
    drive = placement_drive.query.filter_by(id = drive_id, is_active = True).first()

    existing_application = application.query.filter_by(student_id = current_student.user_id, placement_drive_id = drive.id).first()
    if existing_application:
        return jsonify({"error": "Application already submitted!"}), 403
    
    if not drive.is_active:
        return jsonify({"error": "This Drive has been closed!"}), 403
    
    cgpa = get_student_cgpa()
    if drive.min_cgpa > cgpa:
        return jsonify({"error": "You are not eligible to apply to this drive!"}), 403
    
    try:
        new_application = application(
            student_id = current_student.user_id,
            placement_drive_id = drive.id
        )

        db.session.add(new_application)
        db.session.commit()

        cache.delete('admin_all_stats')
        cache.delete('admin_five_drives')
        cache.delete('admin_all_drives')
        cache.delete('admin_five_applications')
        cache.delete('admin_all_applications')
        cache.delete('admin_all_search')

        return jsonify({"message": "Application submitted successfully"}), 200
    
    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({"error": "Unexpected error! Application can't be submitted!"}), 403
    
@student_bp.route('/applications/export', methods=['POST'])
@login_required
@role_required('student')
def trigger_export():
    task = export_student_applications_csv.delay(current_user.id)
    return jsonify({"task_id": task.id}), 202

@student_bp.route('/export/status/<task_id>', methods=['GET'])
@login_required
def check_export_status(task_id):
    task = AsyncResult(task_id, app=current_app.extensions["celery"])
    
    if task.state == 'PENDING':
        return jsonify({"state": task.state, "message": "Task is waiting..."})
    elif task.state == 'SUCCESS':
        return jsonify({
            "state": task.state, 
            "filename": task.result.get("filename")
        })
    else:
        return jsonify({"state": task.state, "error": str(task.info)}), 500



    