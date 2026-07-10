from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import cache
from sqlalchemy.orm import aliased
from app.models import db, user, company, student, placement_drive, application
from app.utils import role_required

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/dashboard', methods=['GET'])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_all_stats')
def get_dashboard_stats():
    student_count = student.query.join(user).filter_by(is_active=True).count()
    company_count = company.query.join(user).filter(user.is_active == True, company.is_approved == True, company.is_rejected == False).count()
    drive_count = placement_drive.query.join(company).join(user).filter(placement_drive.is_approved == True, placement_drive.is_active == True, user.is_active == True).count()
    pending_companies = company.query.filter_by(is_approved=False, is_rejected=False).count()
    pending_drives = placement_drive.query.filter_by(is_approved=False, is_rejected=False).count()
    blacklisted_students = student.query.join(user).filter(user.is_deleted == False, student.is_blacklisted == True).count()
    blacklisted_companies = company.query.join(user).filter(user.is_deleted==False, company.is_blacklisted==True, company.is_approved==True).count()

    student_user = aliased(user, name="student_user")
    company_user = aliased(user, name="company_user")

    all_application_count = application.query\
        .join(student, application.student_id == student.user_id)\
        .join(student_user, student.user_id == student_user.id)\
        .join(placement_drive, application.placement_drive_id == placement_drive.id)\
        .join(company, placement_drive.company_id == company.user_id)\
        .join(company_user, company.user_id == company_user.id)\
        .filter(student_user.is_deleted == False, company_user.is_deleted == False).count()
    
    accepted_application_count = application.query\
        .join(student, application.student_id == student.user_id)\
        .join(student_user, student.user_id == student_user.id)\
        .join(placement_drive, application.placement_drive_id == placement_drive.id)\
        .join(company, placement_drive.company_id == company.user_id)\
        .join(company_user, company.user_id == company_user.id)\
        .filter(student_user.is_deleted == False, company_user.is_deleted == False, application.status == 'Accepted').count()
    
    shortlisted_application_count = application.query\
        .join(student, application.student_id == student.user_id)\
        .join(student_user, student.user_id == student_user.id)\
        .join(placement_drive, application.placement_drive_id == placement_drive.id)\
        .join(company, placement_drive.company_id == company.user_id)\
        .join(company_user, company.user_id == company_user.id)\
        .filter(student_user.is_deleted == False, company_user.is_deleted == False, application.status == 'Shortlisted').count()
    
    rejected_application_count = application.query\
        .join(student, application.student_id == student.user_id)\
        .join(student_user, student.user_id == student_user.id)\
        .join(placement_drive, application.placement_drive_id == placement_drive.id)\
        .join(company, placement_drive.company_id == company.user_id)\
        .join(company_user, company.user_id == company_user.id)\
        .filter(student_user.is_deleted == False, company_user.is_deleted == False, application.status == 'Rejected').count()



    return jsonify({
        "active_students": student_count,
        "active_companies": company_count,
        "active_drives": drive_count,
        "pending_companies": pending_companies,
        "pending_drives": pending_drives,
        "blacklisted_students": blacklisted_students,
        "blacklisted_companies": blacklisted_companies,
        "all_applications": all_application_count,
        "shortlisted_applications": shortlisted_application_count,
        "accepted_applications": accepted_application_count,
        "rejected_applications": rejected_application_count
    }), 200

@admin_bp.route('/glance/companies', methods=['GET'])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_five_companies')
def get_five_companies():
    companies = company.query.join(user).filter(user.is_active==True, company.is_approved==True).limit(5).all()
    company_data = [c.to_dict() for c in companies]
    return jsonify({"five_companies": company_data}), 200

@admin_bp.route('/companies', methods=['GET'])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_all_companies')
def get_all_companies():
    active_companies = company.query.join(user).filter(user.is_active==True, company.is_approved==True).all()
    blacklisted_companies = company.query.join(user).filter(user.is_deleted==False, company.is_blacklisted==True, company.is_approved==True).all()
    return jsonify({"active_companies": [c.to_dict() for c in active_companies],
                   "blacklisted_companies": [c.to_dict() for c in blacklisted_companies]}), 200

@admin_bp.route('/pending/companies', methods=['GET'])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_pending_companies')
def get_pending_companies():
    companies = company.query.join(user).filter(
        user.is_active == True,
        company.is_approved == False,
        company.is_rejected == False,
    ).all()
    company_data = [c.to_dict() for c in companies]
    return jsonify({"pending_companies": company_data}), 200

@admin_bp.route('/companies/<int:company_id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_company(company_id):
    c = company.query.filter_by(user_id=company_id).first()
    if not c:
        return jsonify({"error": "Company not found"}), 404
    
    try:
        c.is_approved = True
        c.is_rejected = False
        db.session.commit()

        cache.delete('admin_all_stats')
        cache.delete('admin_five_companies')
        cache.delete('admin_all_companies')
        cache.delete('admin_pending_companies')
        cache.delete('admin_all_search')
        
        return jsonify({"message": f"'{c.company_name}' approved successfully."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Database Approval Error: {e}")
        return jsonify({"error": "An internal database error occurred."}), 500


@admin_bp.route('/companies/<int:company_id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_company(company_id):
    c = company.query.filter_by(user_id=company_id).first()
    if not c:
        return jsonify({"error": "Company not found"}), 404
    
    try:
        c.is_approved = False
        c.is_rejected = True
        db.session.commit()

        cache.delete('admin_all_stats')
        cache.delete('admin_pending_companies')
        cache.delete('admin_all_search')
        
        return jsonify({"message": f"'{c.company_name}' rejected successfully."}), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"Database Rejection Error: {e}")
        return jsonify({"error": "An internal database error occurred."}), 500
    
@admin_bp.route('/company/<int:company_id>/update', methods=['POST'])
@login_required
@role_required('admin')
def update_company(company_id):
    c = company.query.filter_by(user_id=company_id).first()
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

    existing_user = user.query.filter(user.email == email, user.id != company_id).first()
    if existing_user:
        return jsonify({"error": "Email is already registered by another company/user"}), 409

    try:
        c.user.email = email
        c.company_name = company_name
        c.industry = industry
        c.website = website
        db.session.commit()

        cache.delete('admin_five_companies')
        cache.delete('admin_all_companies')
        cache.delete('admin_five_drives')
        cache.delete('admin_all_drives')
        cache.delete('admin_pending_drives')
        cache.delete('admin_five_applications')
        cache.delete('admin_all_applications')
        cache.delete('admin_all_search')

        return jsonify({"message": f"Profile for company '{company_name}' updated successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Company Update Failure Exception: {e}")
        return jsonify({"error": "An internal database error occurred while committing changes."}), 500

@admin_bp.route('/user/<int:user_id>/blacklist', methods=['POST'])
@login_required
@role_required('admin')
def blacklist(user_id):
    user_to_blacklist = user.query.get_or_404(user_id)
    if not user_to_blacklist:
        return jsonify({"error": "Not found"}), 404
    
    try:
        user_to_blacklist.is_active = not user_to_blacklist.is_active
        if user_to_blacklist.role == 'student' and user_to_blacklist.student:
            user_to_blacklist.student.is_blacklisted = not user_to_blacklist.student.is_blacklisted
            status = "blacklisted" if user_to_blacklist.student.is_blacklisted else "removed from blacklist"
        elif user_to_blacklist.role == 'company' and user_to_blacklist.company:
            user_to_blacklist.company.is_blacklisted = not user_to_blacklist.company.is_blacklisted
            status = "blacklisted" if user_to_blacklist.company.is_blacklisted else "removed from blacklist"

        db.session.commit()
        cache.delete('admin_all_stats')
        cache.delete('admin_five_companies')
        cache.delete('admin_all_companies')
        cache.delete('admin_five_students')
        cache.delete('admin_all_students')
        cache.delete('admin_five_drives')
        cache.delete('admin_all_drives')
        cache.delete('admin_pending_drives')
        cache.delete('admin_all_applications')
        cache.delete('admin_five_applications')
        cache.delete('admin_all_search')
        
        if user_to_blacklist.role == 'student':
            return jsonify({"message": f"Student '{user_to_blacklist.student.full_name}' {status} successfully"}), 200
        elif user_to_blacklist.role == 'company':
            return jsonify({"message": f"'{user_to_blacklist.company.company_name}' {status} successfully"}), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"Toggling Error: {e}")
        return jsonify({"error": "An internal database error occurred."}), 500

@admin_bp.route('/glance/students', methods=['GET'])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_five_students')
def get_five_students():
    students = student.query.join(user).filter_by(is_active=True).limit(5).all()
    student_data = [s.to_dict() for s in students]
    return jsonify({"five_students": student_data}), 200

@admin_bp.route('/students', methods=['GET'])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_all_students')
def get_all_students():
    active_students = student.query.join(user).filter_by(is_active=True).all()
    blacklisted_students = student.query.join(user).filter(user.is_deleted == False, student.is_blacklisted == True).all()
    return jsonify({"active_students": [s.to_dict() for s in active_students],
                   "blacklisted_students": [s.to_dict() for s in blacklisted_students]}), 200

@admin_bp.route('/student/<int:student_id>/update', methods=['POST'])
@login_required
@role_required('admin')
def update_student(student_id):
    s = student.query.filter_by(user_id=student_id).first()
    if not s:
        return jsonify({"error": "Student profile not found"}), 404
    
    if not s.user.is_active:
        return jsonify({"error": "Invalid Action"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing parameters or empty JSON payload"}), 400
    
    email = data.get("email", "").strip()
    full_name = data.get("full_name", "").strip()
    roll_number = data.get("roll_number", "").strip()
    branch = data.get("branch", "").strip()
    graduation_year = data.get("graduation_year")
    cgpa = data.get("cgpa")
    age = data.get("age")
    phone = data.get("phone", "").strip()
    linkedin_url = data.get("linkedin_url", "").strip()

    existing_user = user.query.filter(user.email == email, user.id != student_id).first()
    if existing_user:
        return jsonify({"error": "Email is already registered by another student/user"}), 409

    existing_student = student.query.filter(student.roll_number == roll_number, student.user_id != student_id).first()
    if existing_student:
        return jsonify({"error": "Roll Number is already assigned to another student"}), 409

    try:
        s.user.email = email
        s.full_name = full_name
        s.roll_number = roll_number
        s.branch = branch
        s.phone = phone
        s.linkedin_url = linkedin_url
        s.age = int(age)
        if s.graduation_year is not None:
            s.graduation_year = int(graduation_year)
        s.cgpa = float(cgpa)

        db.session.commit()

        cache.delete('admin_five_students')
        cache.delete('admin_all_students')
        cache.delete('admin_five_drives')
        cache.delete('admin_all_drives')
        cache.delete('admin_five_applications')
        cache.delete('admin_all_applications')
        cache.delete('admin_all_search')

        return jsonify({"message": f"Profile for student '{full_name}' updated successfully!"}), 200

    except ValueError:
        return jsonify({"error": "Format validation failed for numeric fields (Age, Year, or CGPA)."}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Student Update Failure Exception: {e}")
        return jsonify({"error": "An internal database error occurred while committing changes."}), 500

@admin_bp.route('/glance/drives', methods=['GET'])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_five_drives')
def get_five_drives():
    drives = placement_drive.query.join(company).join(user).filter(placement_drive.is_approved == True,placement_drive.is_active == True, user.is_active == True).limit(5).all()
    drive_data = [s.to_dict() for s in drives]
    return jsonify({"five_drives": drive_data}), 200

@admin_bp.route('/drives', methods=['GET'])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_all_drives')
def get_all_drives():
    ongoing_drives = placement_drive.query.join(company).join(user).filter(placement_drive.is_approved == True,placement_drive.is_active == True, user.is_active == True).all()
    closed_drives = placement_drive.query.join(company).join(user).filter(placement_drive.is_approved == True,placement_drive.is_active == False, user.is_active == True).all()
    drives_by_blacklisted_companies = placement_drive.query.join(company).join(user).filter(placement_drive.is_approved == True,placement_drive.is_active == False,company.is_blacklisted == True ,user.is_deleted == False).all()
    return jsonify({"ongoing_drives": [d.to_dict() for d in ongoing_drives],
                    "closed_drives": [d.to_dict() for d in closed_drives],
                    "drives_by_blacklisted_companies": [d.to_dict() for d in drives_by_blacklisted_companies]}), 200

@admin_bp.route('/pending/drives', methods=['GET'])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_pending_drives')
def get_pending_drives():
    drives = placement_drive.query.join(company).join(user).filter(
        placement_drive.is_approved == False,
        placement_drive.is_rejected == False,
        placement_drive.is_active == True,
        company.is_approved == True,
        user.is_active == True).all()
    drive_data = [s.to_dict() for s in drives]
    return jsonify({"pending_drives": drive_data}), 200

@admin_bp.route('/drives/<int:drive_id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_drive(drive_id):
    d = placement_drive.query.filter_by(id=drive_id).first()
    if not d:
        return jsonify({"error": "Drive not found"}), 404
    
    try:
        d.is_approved = True
        d.is_rejected = False
        db.session.commit()

        cache.delete('admin_all_stats')
        cache.delete('admin_five_drives')
        cache.delete('admin_all_drives')
        cache.delete('admin_pending_drives')
        cache.delete('admin_all_search')
        
        return jsonify({"message": f"Drive '{d.id}' approved successfully."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Database Approval Error: {e}")
        return jsonify({"error": "An internal database error occurred."}), 500
    
@admin_bp.route('/drives/<int:drive_id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_drive(drive_id):
    d = placement_drive.query.filter_by(id=drive_id).first()
    if not d:
        return jsonify({"error": "Drive not found"}), 404
    
    try:
        d.is_approved = False
        d.is_rejected = True
        d.is_active = False
        db.session.commit()  

        cache.delete('admin_all_stats')
        cache.delete('admin_pending_drives')
        cache.delete('admin_all_search')

        return jsonify({"message": f"Drive '{d.id}' rejected successfully."}), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"Database Rejection Error: {e}")
        return jsonify({"error": "An internal database error occurred."}), 500

@admin_bp.route('/glance/applications', methods=["GET"])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_five_applications')
def get_five_applications():
    student_user = aliased(user, name="student_user")
    company_user = aliased(user, name="company_user")

    apps = application.query\
        .join(student, application.student_id == student.user_id)\
        .join(student_user, student.user_id == student_user.id)\
        .join(placement_drive, application.placement_drive_id == placement_drive.id)\
        .join(company, placement_drive.company_id == company.user_id)\
        .join(company_user, company.user_id == company_user.id)\
        .filter(
            placement_drive.is_active == True,
            student_user.is_active == True,
            company_user.is_active == True,
            company.is_approved == True).all()

    all_apps = []
    for app in apps:
        app_data = {**app.student.to_dict(), **app.placement_drive.to_dict(), **app.placement_drive.company.to_dict(), **app.to_dict()}
        all_apps.append(app_data)
    
    return ({"five_applications": all_apps}), 200

@admin_bp.route('/applications', methods=["GET"])
@login_required
@role_required('admin')
@cache.cached(timeout=600, key_prefix='admin_all_applications')
def get_all_applications():

    student_user = aliased(user, name="student_user")
    company_user = aliased(user, name="company_user")

    all_apps = application.query\
        .join(student, application.student_id == student.user_id)\
        .join(student_user, student.user_id == student_user.id)\
        .join(placement_drive, application.placement_drive_id == placement_drive.id)\
        .join(company, placement_drive.company_id == company.user_id)\
        .join(company_user, company.user_id == company_user.id).all()

    current_apps = []
    apps_for_closed_drives = []
    apps_for_blacklisted_companies = []
    apps_by_blacklisted_students = []

    for app in all_apps:
        app_data = {**app.student.to_dict(), **app.to_dict(), **app.placement_drive.to_dict(), **app.placement_drive.company.to_dict()}

    if student_user.is_active and company_user.is_active and company.is_approved:
        if placement_drive.is_active:
            current_apps.append(app_data)
        else:
            apps_for_closed_drives.append(app_data)
    
    elif not company_user.is_deleted and company.is_blacklisted and company.is_approved == True:
        apps_for_blacklisted_companies.append(app_data)

    elif student.is_blacklisted and not student_user.is_deleted:
        apps_by_blacklisted_students.append(app_data)

    return jsonify({"current_applications": current_apps,
                    "applications_for_closed_drives": apps_for_closed_drives,
                    "applications_for_blacklisted_companies": apps_for_blacklisted_companies,
                    "applications_by_blacklisted_students": apps_by_blacklisted_students}), 200
        
@admin_bp.route("/user/<int:id>/delete", methods=["DELETE"])
@login_required
@role_required('admin')
def delete_user(id):
    """Soft deletes a user account and updates their specific role profile."""
    user_to_delete = user.query.get_or_404(id)

    # Prevent the admin from deleting themselves
    if user_to_delete.id == current_user.id:
        return jsonify({"error": "You cannot delete your own admin account."}), 400

    # Soft delete
    user_to_delete.is_deleted = True
    user_to_delete.is_active = False
    
    user_to_delete.email = f"{user_to_delete.email}_deleted_{user_to_delete.id}"
    user_to_delete.password = "deleted"
    
    if user_to_delete.role == "student" and user_to_delete.student:
        user_to_delete.student.is_blacklisted = True
    elif user_to_delete.role == "company" and user_to_delete.company:
        user_to_delete.company.is_approved = False
        user_to_delete.company.is_rejected = True

    try:
        db.session.commit()

        cache.delete('admin_all_stats')
        cache.delete('admin_five_companies')
        cache.delete('admin_all_companies')
        cache.delete('admin_five_students')
        cache.delete('admin_all_students')
        cache.delete('admin_five_drives')
        cache.delete('admin_all_drives')
        cache.delete('admin_pending_drives')
        cache.delete('admin_all_applications')
        cache.delete('admin_five_applications')
        cache.delete('admin_all_search')

        return jsonify({"message": "User deactivated successfully."}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An error occurred while deactivating the user. Please try again."}), 500
    
@admin_bp.route('/search/all', methods=['GET'])
@login_required
@role_required('admin')
@cache.cached(timeout=60, key_prefix='admin_all_search', query_string=True)
def global_search():

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"error": "Type something in the search bar"}), 400

    search_term = f"%{query}%"

    active_students = student.query.join(user).filter(
        user.is_active == True,
        or_(
            student.full_name.ilike(search_term),
            student.roll_number.ilike(search_term),
            student.branch.ilike(search_term)
        )
    ).all()

    blacklisted_students = student.query.join(user).filter(
        student.is_blacklisted == True, user.is_deleted == False,
        or_(
            student.full_name.ilike(search_term),
            student.roll_number.ilike(search_term),
            student.branch.ilike(search_term)
        )
    ).all()

    active_companies = company.query.join(user).filter(
        user.is_active == True,
        company.is_approved == True,
        or_(
            company.company_name.ilike(search_term),
            company.industry.ilike(search_term)
        )
    ).all()

    pending_companies = company.query.join(user).filter(
        user.is_active == True,
        company.is_approved == False,
        company.is_rejected == False,
        or_(
            company.company_name.ilike(search_term),
            company.industry.ilike(search_term)
        )
    ).all()

    blacklisted_companies = company.query.join(user).filter(
        company.is_blacklisted == True, user.is_deleted == False,
        or_(
            company.company_name.ilike(search_term),
            company.industry.ilike(search_term)
        )
    ).all()

    ongoing_drives = placement_drive.query.join(company).join(user).filter(
        placement_drive.is_approved == True,
        placement_drive.is_active == True,
        company.is_approved == True,
        user.is_active == True,
        or_(
            placement_drive.job_title.ilike(search_term),
            placement_drive.location.ilike(search_term),
            company.company_name.ilike(search_term)
        )
    ).all()

    closed_drives = placement_drive.query.join(company).join(user).filter(
        placement_drive.is_approved == True,
        placement_drive.is_active == False,
        company.is_approved == True,
        user.is_active == True,
        or_(
            placement_drive.job_title.ilike(search_term),
            placement_drive.location.ilike(search_term),
            company.company_name.ilike(search_term)
        )
    ).all()

    drives_by_blaclisted_companies = placement_drive.query.join(company).join(user).filter(
        company.is_blacklisted == True,
        user.is_deleted == False,
        or_(
            placement_drive.job_title.ilike(search_term),
            placement_drive.location.ilike(search_term),
            company.company_name.ilike(search_term)
        )
    ).all()

    pending_drives = placement_drive.query.join(company).join(user).filter(
        placement_drive.is_approved == False,
        placement_drive.is_rejected == False,
        placement_drive.is_active == True,
        company.is_approved == True,
        user.is_active == True,
        or_(
            placement_drive.job_title.ilike(search_term),
            placement_drive.location.ilike(search_term),
            company.company_name.ilike(search_term)
        )
    ).all()

    student_user = aliased(user, name="student_user")
    company_user = aliased(user, name="company_user")

    all_apps = application.query\
        .join(student, application.student_id == student.user_id)\
        .join(student_user, student.user_id == student_user.id)\
        .join(placement_drive, application.placement_drive_id == placement_drive.id)\
        .join(company, placement_drive.company_id == company.user_id)\
        .join(company_user, company.user_id == company_user.id)\
        .filter(
            or_(
                placement_drive.job_title.ilike(search_term),
                student.full_name.ilike(search_term),     
                student.roll_number.ilike(search_term),
                company.company_name.ilike(search_term)
            )
        ).all()
    
    current_apps = []
    apps_for_closed_drives = []
    apps_for_blacklisted_companies = []
    apps_by_blacklisted_students = []

    for app in all_apps:
        app_data = {**app.student.to_dict(), **app.to_dict(), **app.placement_drive.to_dict(), **app.placement_drive.company.to_dict()}

    if student_user.is_active and company_user.is_active and company.is_approved:
        if placement_drive.is_active:
            current_apps.append(app_data)
        else:
            apps_for_closed_drives.append(app_data)
    
    elif not company_user.is_deleted and company.is_blacklisted and company.is_approved == True:
        apps_for_blacklisted_companies.append(app_data)

    elif student.is_blacklisted and not student_user.is_deleted:
        apps_by_blacklisted_students.append(app_data)
    
    if not active_students and not blacklisted_students and not active_companies and not blacklisted_companies and not pending_companies and not ongoing_drives and not closed_drives and not drives_by_blaclisted_companies and not pending_drives and not current_apps and not apps_for_closed_drives and not apps_for_blacklisted_companies and not apps_by_blacklisted_students:
        return jsonify({"error": "Search term has no match!"}), 404

    return jsonify({
        "active_students": [s.to_dict() for s in active_students],
        "blacklisted_students": [s.to_dict() for s in blacklisted_students],
        "active_companies": [c.to_dict() for c in active_companies],
        "pending_companies": [c.to_dict() for c in pending_companies],
        "blacklisted_companies": [c.to_dict() for c in blacklisted_companies],
        "ongoing_drives": [d.to_dict() for d in ongoing_drives],
        "closed_drives": [d.to_dict() for d in closed_drives],
        "drives_by_blacklisted_companies": [d.to_dict() for d in drives_by_blaclisted_companies],
        "pending_drives": [d.to_dict() for d in pending_drives],
        "current_applications":  current_apps,
        "applications_for_closed_drives": apps_for_closed_drives,
        "applications_for_blacklisted_companies": apps_for_blacklisted_companies,
        "applications_by_blacklisted_students": apps_by_blacklisted_students,
    }), 200


