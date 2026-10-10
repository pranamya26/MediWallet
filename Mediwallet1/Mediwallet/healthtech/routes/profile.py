from datetime import date
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")

# Fields that can be freely updated by the patient
_PERSONAL_FIELDS = ["full_name", "gender", "phone"]
_MEDICAL_FIELDS = ["blood_group", "allergies", "conditions", "current_medicines"]
_EMERGENCY_FIELDS = ["emergency_contact_name", "emergency_contact_phone", "emergency_contact_relation"]


@profile_bp.get("/")
@login_required
def get_profile():
    """Return the full patient profile."""
    return jsonify(profile=current_user.to_dict()), 200


@profile_bp.put("/")
@login_required
def update_profile():
    """
    Update one or more profile fields.
    All fields are optional — only those present in the body are changed.
    Body may include: full_name, gender, phone, date_of_birth (YYYY-MM-DD),
                      blood_group, allergies, conditions, current_medicines,
                      emergency_contact_name, emergency_contact_phone, emergency_contact_relation
    """
    data = request.get_json(silent=True) or {}

    # ── Personal fields ───────────────────────────────────────────────────────
    for field in _PERSONAL_FIELDS:
        if field in data:
            setattr(current_user, field, data[field])

    # ── Date of birth with format validation ──────────────────────────────────
    if "date_of_birth" in data:
        if data["date_of_birth"] is None:
            current_user.date_of_birth = None
        else:
            try:
                current_user.date_of_birth = date.fromisoformat(data["date_of_birth"])
            except ValueError:
                return jsonify(error="Invalid date_of_birth. Use YYYY-MM-DD format."), 400

    # ── Medical profile ───────────────────────────────────────────────────────
    for field in _MEDICAL_FIELDS:
        if field in data:
            setattr(current_user, field, data[field])

    # ── Emergency contact ─────────────────────────────────────────────────────
    for field in _EMERGENCY_FIELDS:
        if field in data:
            setattr(current_user, field, data[field])

    db.session.commit()
    return jsonify(message="Profile updated successfully", profile=current_user.to_dict()), 200


@profile_bp.get("/completeness")
@login_required
def profile_completeness():
    """
    Return a completeness checklist so the frontend can prompt the patient
    to fill in missing but important fields.
    """
    u = current_user
    checks = {
        "date_of_birth": bool(u.date_of_birth),
        "phone": bool(u.phone),
        "blood_group": bool(u.blood_group),
        "allergies": bool(u.allergies),
        "conditions": bool(u.conditions),
        "current_medicines": bool(u.current_medicines),
        "emergency_contact": bool(u.emergency_contact_phone),
    }
    score = sum(checks.values())
    total = len(checks)
    return jsonify(
        completeness_percent=round(score / total * 100),
        missing=[k for k, v in checks.items() if not v],
        checks=checks,
    ), 200
