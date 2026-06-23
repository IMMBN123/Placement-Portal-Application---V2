from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class user(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.Date, default=date.today)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active
        }
    
class student(db.Model):
    __tablename__ = 'students'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    roll_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False, index=True)
    age = db.Column(db.Integer, nullable=False)
    branch = db.Column(db.String(50), nullable=False, index=True)
    graduation_year = db.Column(db.Integer, nullable=False)
    cgpa = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(15))
    resume_link = db.Column(db.String(255))
    linkedin_url = db.Column(db.String(255))
    is_blacklisted = db.Column(db.Boolean, default=False)

    user = db.relationship('user', backref=db.backref('student', uselist=False, cascade='all, delete'))

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'email': self.user.email,
            'roll_number': self.roll_number,
            'full_name': self.full_name,
            'age': self.age,
            'branch': self.branch,
            'graduation_year': self.graduation_year,
            'cgpa': self.cgpa,
            'phone': self.phone,
            'resume_link': self.resume_link,
            'linkedin_url': self.linkedin_url,
            'is_blacklisted': self.is_blacklisted
        }

class company(db.Model):
    __tablename__ = 'companies'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    company_name = db.Column(db.String(100), nullable=False, index=True)
    industry = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text)
    website = db.Column(db.String(255))
    phone = db.Column(db.String(15))
    is_approved = db.Column(db.Boolean, default=False)
    is_rejected = db.Column(db.Boolean, default=False)
    is_blacklisted = db.Column(db.Boolean, default=False)

    user = db.relationship('user', backref=db.backref('company', uselist=False, cascade='all, delete'))

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'email': self.user.email,
            'company_name': self.company_name,
            'industry': self.industry,
            'description': self.description,
            'website': self.website,
            'phone': self.phone,
            'is_approved': self.is_approved,
            'is_rejected': self.is_rejected,
            'is_blacklisted': self.is_blacklisted
        }

class placement_drive(db.Model):
    __tablename__ = 'placement_drives'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.user_id'), nullable=False)
    job_title = db.Column(db.String(100), nullable=False, index=True)
    job_description = db.Column(db.Text, nullable=False)
    package_lpa = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False, index=True)
    vacancies = db.Column(db.Integer, nullable = False)
    min_cgpa = db.Column(db.Float)
    deadline = db.Column(db.Date, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    is_rejected = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.Date, default=date.today())

    company = db.relationship('company', backref=db.backref('placement_drives', cascade='all, delete'))

    def is_open(self):
        return self.is_active and self.deadline >= date.today()
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'company_name': self.company.company_name if self.company else None,
            'job_title': self.job_title,
            'job_description': self.job_description,
            'package_lpa': self.package_lpa,
            'location': self.location,
            'vacancies': self.vacancies,
            'min_cgpa': self.min_cgpa,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'is_approved': self.is_approved,
            'is_open': self.is_open(),
            'created_at': f"{self.created_at.day} {self.created_at.strftime('%B %Y')}" if self.created_at else None
        }

class application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.user_id'), nullable=False)
    placement_drive_id = db.Column(db.Integer, db.ForeignKey('placement_drives.id'), nullable=False)
    applied_at = db.Column(db.Date, default=date.today())
    status = db.Column(db.String(20), default='Applied')

    __table_args__ = (db.UniqueConstraint('student_id', 'placement_drive_id', name='unique_application'),)

    student = db.relationship('student', backref=db.backref('applications', cascade='all, delete'))
    placement_drive = db.relationship('placement_drive', backref=db.backref('applications', cascade='all, delete'))
    remarks = db.Column(db.String(255), default='New Application', server_default='New Application')


    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'placement_drive_id': self.placement_drive_id,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'status': self.status,
            'job_title': self.placement_drive.job_title if self.placement_drive else None,
            'remarks': self.remarks
        }
