import os
from flask import Flask, jsonify
from flask_login import LoginManager
from config import Config
from models import db
from models.user import User
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.records import records_bp
from routes.sharing import sharing_bp
from routes.emergency import emergency_bp
from routes.pages import pages_bp


def create_app(config_class=Config) -> Flask:
    """
    Application factory.
    Pass a different config_class (e.g. TestingConfig) in tests.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Ensure upload directory exists ────────────────────────────────────────
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    # ── Login manager callbacks ───────────────────────────────────────────────
    @login_manager.user_loader
    def load_user(uid: str):
        return User.query.get(int(uid))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify(error="Authentication required. Please log in."), 401

    # ── Blueprints ────────────────────────────────────────────────────────────
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(sharing_bp)
    app.register_blueprint(emergency_bp)

    # ── Global error handlers ─────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Resource not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify(error="Method not allowed"), 405

    @app.errorhandler(413)
    def payload_too_large(e):
        return jsonify(error="File too large. Maximum upload size is 16 MB."), 413

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(error="An internal server error occurred."), 500

    # ── Create DB tables (safe for existing tables) ───────────────────────────
    with app.app_context():
        db.create_all()

    return app
app = create_app()
if __name__ == "__main__":
    
    app.run(debug=True, host="0.0.0.0", port=5000)
