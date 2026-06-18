from flask import Flask, jsonify, render_template
from flask_login import LoginManager
from config import Config
from app.models import db, user 
import os
from dotenv import load_dotenv

load_dotenv()

login_manager = LoginManager()

def create_app():
    # Initialise flask app
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Return JSON error instead of redirecting to a login page
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    # Register Blueprints
    from app.api.auth import auth_bp
    from app.api.admin import admin_bp
    from app.api.company import company_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(company_bp)

    try:
        from utils import auto_close_expired_drives
        @app.before_request
        def handle_drive_expiry():
            auto_close_expired_drives()
    except ImportError:
        pass

    # Catch-all route to serve the Vue.js SPA
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        if path.startswith('api/'):
            return jsonify({"error": "API Endpoint Not Found"}), 404
        # Otherwise, serve the Vue.js app
        return render_template('index.html')
    
    with app.app_context():
        db.create_all()

        # Admin creation
        admin_email = "admin@portal.com"
        admin_password = os.getenv("ADMIN_PASSWORD")

        existing_admin = user.query.filter_by(email=admin_email).first()

        if not existing_admin:
            if not admin_password:
                raise ValueError("ADMIN_PASSWORD environment variable is not set.")
            admin_user = user(email=admin_email, role='admin')
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()

            print("Admin user created")
            
    return app

@login_manager.user_loader
def load_user(user_id):
    return user.query.get(int(user_id))