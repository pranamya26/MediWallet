from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    """
    Create a new patient account.
    Body: { email, password, full_name }
    """
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()

    # ── Validation ────────────────────────────────────────────────────────────
    if not email or not password or not full_name:
        return jsonify(error="email, password, and full_name are required"), 400

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(error="Invalid email address"), 400

    if len(password) < 8:
        return jsonify(error="Password must be at least 8 characters"), 400

    if User.query.filter_by(email=email).first():
        return jsonify(error="An account with this email already exists"), 409

    # ── Create user ───────────────────────────────────────────────────────────
    user = User(email=email, full_name=full_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user, remember=True)
    return jsonify(message="Registration successful", user=user.to_dict()), 201


@auth_bp.post("/login")
def login():
    """
    Authenticate an existing patient.
    Body: { email, password, remember? }
    """
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify(error="email and password are required"), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify(error="Invalid email or password"), 401

    remember = bool(data.get("remember", False))
    login_user(user, remember=remember)
    return jsonify(message="Login successful", user=user.to_dict()), 200


@auth_bp.post("/logout")
@login_required
def logout():
    """End the current session."""
    logout_user()
    return jsonify(message="Logged out successfully"), 200


@auth_bp.get("/me")
@login_required
def me():
    """Return the currently authenticated patient's data."""
    return jsonify(user=current_user.to_dict()), 200


@auth_bp.post("/change-password")
@login_required
def change_password():
    """
    Change password for the logged-in user.
    Body: { current_password, new_password }
    """
    data = request.get_json(silent=True) or {}
    current_pw = data.get("current_password", "")
    new_pw = data.get("new_password", "")

    if not current_user.check_password(current_pw):
        return jsonify(error="Current password is incorrect"), 401

    if len(new_pw) < 8:
        return jsonify(error="New password must be at least 8 characters"), 400

    current_user.set_password(new_pw)
    db.session.commit()
    return jsonify(message="Password changed successfully"), 200
