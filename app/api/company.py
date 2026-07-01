from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm import aliased
from app.models import db, user, company, student, placement_drive, application
from app.utils import role_required
from datetime import datetime

company_bp = Blueprint('company', __name__, url_prefix='/api/company')

@company_bp.route('/dashboard', methods=['GET'])
@login_required
@role_required('company')
def get_dashboard_stats():
    active_drive_count = placement_drive.query.join(company).filter(current_user.id == company.user_id, placement_drive.is_approved == True, placement_drive.is_active == True).count()
    closed_drive_count = placement_drive.query.join(company).filter(current_user.id == company.user_id, placement_drive.is_approved == True, placement_drive.is_active == False).count()
    pending_drive_count = placement_drive.query.join(company).filter(current_user.id == company.user_id, placement_drive.is_approved == False, placement_drive.is_rejected == False).count()
    new_application_count = application.query.join(placement_drive).join(company).join(user).filter(current_user.id == company.user_id, user.is_active == True, placement_drive.is_active == True, application.status == 'Applied').count()
    rejected_drive_count = placement_drive.query.join(company).filter(current_user.id == company.user_id, placement_drive.is_approved == False, placement_drive.is_rejected == True).count()
    shortlist_application_count = application.query.join(placement_drive).join(company).join(user).filter(current_user.id == company.user_id, user.is_active == True, placement_drive.is_active == True, application.status == 'Shortlisted').count()
    accept_application_count = application.query.join(placement_drive).join(company).join(user).filter(current_user.id == company.user_id, user.is_active == True, placement_drive.is_approved == True, application.status == 'Accepted').count()
    reject_application_count = application.query.join(placement_drive).join(company).join(user).filter(current_user.id == company.user_id, user.is_active == True, placement_drive.is_approved == True, application.status == 'Rejected').count()
    return jsonify({
        "active_drives": active_drive_count,
        "pending_drives": pending_drive_count,
        "closed_drives": closed_drive_count,
        "new_applications": new_application_count,
        "rejected_drives": rejected_drive_count,
        "shortlisted_applications": shortlist_application_count,
        "accepted_applications": accept_application_count,
        "rejected_applications": reject_application_count,
    }), 200

@company_bp.route("/create-drive", methods = ["POST"])
@login_required
@role_required("company")
def create_drive():
    if request.method == "POST":
        job_title = request.form.get('job_title')
        job_description = request.form.get('job_description')
        min_cgpa = float(request.form.get('min_cgpa'))
        package_lpa = request.form.get('package_lpa')
        vacancies = int(request.form.get('vacancies'))
        location = request.form.get('location')
        deadline = datetime.strptime(
                request.form.get("deadline"),
                "%Y-%m-%d")
        
        if deadline < datetime.now():
            return jsonify({"error":"Deadline cannot be in past"}), 400

        if min_cgpa < 0 or min_cgpa > 10:
            return jsonify({"error":"Invalid CGPA range"}), 400
        
        if vacancies < 1 :
            return jsonify({"error":"Atleast 1 post vacancy should be present"}), 400
        
        # Duplicate drive check
        existing_active_drive = placement_drive.query.filter_by(
            company_id=current_user.id,
            job_title=job_title,
            package_lpa=package_lpa,
            is_active=True
        ).first()

        if existing_active_drive:
            return jsonify({"error":"An active drive with same job title and package already exists."}), 403

        
        drive = placement_drive(
            job_title = job_title,
            job_description = job_description,
            min_cgpa = min_cgpa,
            package_lpa = package_lpa,
            vacancies = vacancies,
            location = location,
            deadline = deadline,
            company_id = current_user.id
        )

        db.session.add(drive)
        db.session.commit()

        return jsonify({"message":"Drive created successfully. Await admin approval!"}), 200
    
@company_bp.route('/drives', methods = ['GET'])
@login_required
@role_required('company')
def get_drives():
    ongoing_drives = placement_drive.query.join(company).filter(current_user.id == company.user_id, placement_drive.is_approved == True, placement_drive.is_active == True).all()
    pending_drives = placement_drive.query.join(company).filter(current_user.id == company.user_id, placement_drive.is_approved == False, placement_drive.is_rejected == False).all()
    closed_drives = placement_drive.query.join(company).filter(current_user.id == company.user_id, placement_drive.is_approved == True, placement_drive.is_active == False).all()
    rejected_drives = placement_drive.query.join(company).filter(current_user.id == company.user_id, placement_drive.is_approved == False, placement_drive.is_rejected == True).all()

    return jsonify({"ongoing_drives": [d.to_dict() for d in ongoing_drives],
                    "pending_drives": [d.to_dict() for d in pending_drives],
                    "closed_drives": [d.to_dict() for d in closed_drives],
                    "rejected_drives": [d.to_dict() for d in rejected_drives]}), 200

@company_bp.route('/profile', methods=['GET'])
@login_required
@role_required('company')
def get_company():
    profile = company.query.filter_by(user_id=current_user.id).first_or_404()
    return jsonify(profile.to_dict()), 200

@company_bp.route('/update', methods=['POST'])
@login_required
@role_required('company')
def self_update_company():
    c = company.query.filter_by(user_id=current_user.id).first_or_404()
    if not c:
        return jsonify({"error": "Company profile not found"}), 404
    
    if not c.user.is_active:
        return jsonify({"error": "Invalid Action"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing parameters or empty JSON payload"}), 400
    
    email = data.get("email", "").strip()
    company_name = data.get("company_name", "").strip()
    industry = data.get("industry", "").strip()
    website = data.get("website", "").strip()
    phone = data.get("phone", "").strip()
    description = data.get("description", "").strip()

    existing_user = user.query.filter(user.email == email, user.id != current_user.id).first()
    if existing_user:
        return jsonify({"error": "Email is already registered by another company/user"}), 409

    try:
        c.user.email = email
        c.company_name = company_name
        c.industry = industry
        c.website = website
        c.phone = phone
        c.description = description
        db.session.commit()
        return jsonify({"message": f"Profile for company '{company_name}' updated successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Company Update Failure Exception: {e}")
        return jsonify({"error": "An internal database error occurred while committing changes."}), 500
    
@company_bp.route("/drives/<int:drive_id>/close", methods=["POST"])
@login_required
@role_required("company")
def close_drive(drive_id):
    drive = placement_drive.query.get_or_404(drive_id)

    drive.is_active = False
    db.session.commit()
    return jsonify({"message": "Drive Closed successfully"}), 200

@company_bp.route("/drives/<int:drive_id>/app-count", methods=["GET"])
@login_required
@role_required("company")
def get_application_count(drive_id):
    application_count = application.query.join(placement_drive).filter(placement_drive.id == drive_id).count()
    return jsonify({"count": application_count}), 200

@company_bp.route("/drives/<int:drive_id>/applications", methods=["GET"])
@login_required
@role_required("company")
def get_applications(drive_id):
    all_apps = application.query.join(student).join(user).filter(
        application.placement_drive_id == drive_id,
        user.is_active == True,
    ).all()

    new_apps = []
    accepted_apps = []
    shortlisted_apps = []
    rejected_apps = []

    for app in all_apps:
        # Combines all columns of both tables into a unified JSON object
        app_data = {**app.student.to_dict(), **app.to_dict(), **app.placement_drive.to_dict(), **app.placement_drive.company.to_dict()}
        
        status_lower = app.status.lower()
        if status_lower == 'applied':
            new_apps.append(app_data)
        elif status_lower == 'accepted':
            accepted_apps.append(app_data)
        elif status_lower == 'shortlisted':
            shortlisted_apps.append(app_data)
        elif status_lower == 'rejected':
            rejected_apps.append(app_data)

    return jsonify({
        "new_applications": new_apps,
        "accepted_applications": accepted_apps,
        "shortlisted_applications": shortlisted_apps,
        "rejected_applications": rejected_apps
    }), 200

@company_bp.route('/applications/<int:app_id>/update', methods=['POST'])
@login_required
@role_required('company')
def update_app_status(app_id):
    app = application.query.get_or_404(app_id)

    if app.placement_drive.company_id != current_user.id:
        return jsonify({"error": "Unauthorized Action"}), 403
    
    data = request.get_json()
    
    try:
        new_status = data.get('status').strip()
        remark = data.get('remarks').strip()

        app.status = new_status
        app.remarks = remark

        db.session.commit()
        return jsonify({"message": f"Application Status was successfully updated to '{new_status}'"}), 200
    
    except Exception as e:
        db.session.rollback()
        print("Error while updating status:", e)
        return jsonify({"error": "An internal database error occurred while saving updates.", "details": str(e)}), 500