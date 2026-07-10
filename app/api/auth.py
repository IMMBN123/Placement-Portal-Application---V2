from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import cache
from app.models import db, user, company, student
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
import uuid
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Missing email or password"}), 400
    
    u = user.query.filter_by(email=data.get('email')).first()

    if not u:
        return jsonify({"error": "Invalid email"}), 401
    elif not u.check_password(data.get('password')):
        return jsonify({"error": "Incorrect password"}), 401
    elif u.is_deleted:
        return jsonify({"error": "Account is deactivated. Contact admin"}), 403
    else:
        if u.role == 'company':
            if u.company:
                if u.company.is_blacklisted:
                        return jsonify({"error": "Your company has been blacklisted! Contact admin."}), 403
                if u.company.is_rejected:
                        return jsonify({"error": "Your company registration was rejected."}), 403
                if not u.company.is_approved:
                    return jsonify({"error": "Your company registration is pending admin approval."}), 403
            else:
                return jsonify({"error": "Company profile missing"}), 500
        elif u.role == 'student':
            if u.student:
                if u.student.is_blacklisted:
                    return jsonify({"error": "You has been blacklisted! Contact admin."}), 403
            else:
                 return jsonify({"error": "Student profile missing"}), 500
            
        login_user(u)

        return jsonify({
                "message": "Login successful",
                "user": u.to_dict()
        }), 200
        
@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
     logout_user
     return jsonify({"message": "Logged out successfully"}), 200

@auth_bp.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    return jsonify({'error': 'File size too large'})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@auth_bp.route('/register/student', methods=[ 'POST'])
def register_student():

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        roll_number = request.form.get('roll_number')
        age = request.form.get('age')
        branch = request.form.get('branch')
        graduation_year = request.form.get('graduation_year')
        cgpa = request.form.get('cgpa')
        phone = request.form.get('phone')
        linkedin_url = request.form.get('linkedin_url')

        file = request.files.get('resume_link')

        filename = None
        resume_link = None

        if file and allowed_file(file.filename):
            filename = f"{roll_number}_{uuid.uuid4()}_{secure_filename(file.filename)}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        resume_link = filename

        existing_user = user.query.filter_by(email=email).first()

        if existing_user:
            return jsonify({"error": "Email already registered. Please log in."}), 409

        try:

            new_user = user(email=email, role='student')
            new_user.set_password(password)

            new_student = student(
                user=new_user,
                full_name=full_name,
                roll_number=roll_number,
                age=age,
                branch=branch,
                graduation_year=graduation_year,
                cgpa=cgpa,
                phone=phone,
                resume_link=resume_link,
                linkedin_url=linkedin_url
            )

            db.session.add(new_user)
            db.session.add(new_student)
            db.session.commit()

            cache.delete('admin_all_stats')
            cache.delete('admin_five_students')
            cache.delete('admin_all_students')
            cache.delete('admin_all_search')

            return jsonify({"message": "Registration successful!"}), 201

        except Exception as e:
            db.session.rollback()
            print(e)
            return jsonify({"error": "An error occurred during registration."}), 500
        
@auth_bp.route('/register/company', methods=['POST'])
def register_company():
    email = request.form.get('email')
    password = request.form.get('password')
    company_name = request.form.get('company_name')
    industry = request.form.get('industry')
    description = request.form.get('description')
    website = request.form.get('website')
    phone = request.form.get('phone')

    # Check if user already exists
    existing_user = user.query.filter_by(email=email).first()
    if existing_user:
            return jsonify({"error": "Email already registered. Please log in."}), 409
    
    try:
        new_user = user(email=email, role='company')
        new_user.set_password(password)

        
        
        new_company = company(user=new_user, 
                        company_name=company_name, 
                        industry=industry, 
                        description=description, 
                        website=website, 
                        phone=phone)
        
        db.session.add(new_user)
        db.session.add(new_company)
        db.session.commit()

        cache.delete('admin_all_stats')
        cache.delete('admin_all_companies')
        cache.delete('admin_pending_companies')
        cache.delete('admin_five_students')
        cache.delete('admin_all_search')

        return jsonify({'message': 'Registration successful! Awaiting admin approval'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred during registration."}), 500



@auth_bp.route('/me', methods=['GET'])
def get_current_user():
     if current_user.is_authenticated:
          return jsonify({
               "authenticated": True,
               "user": current_user.to_dict()
          }), 200
     
     return jsonify({"authenticated": False}), 401
        
