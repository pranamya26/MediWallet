from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models.medical_record import MedicalRecord

emergency_bp = Blueprint("emergency", __name__, url_prefix="/api")


def _field(value, source: str) -> dict:
    """
    Wrap a patient-reported value with a status tag.
    The UI must show 'missing' or 'unverified' labels clearly so clinicians
    know not to treat absent data as confirmed-safe.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return {"value": None, "source": source, "status": "missing"}
    return {"value": value, "source": source, "status": "present"}


@emergency_bp.get("/emergency-summary")
@login_required
def emergency_summary():
    """
    Return a concise, high-priority view of the patient's health information
    for use in emergency or fast-consultation scenarios.

    All values are patient-reported unless explicitly confirmed by a clinician.
    The disclaimer field must be shown prominently in the UI.
    """
    u = current_user

    # Five most recent records (any type) sorted by document_date then upload time
    recent_records = (
        MedicalRecord.query
        .filter_by(patient_id=u.id, is_deleted=False)
        .order_by(
            MedicalRecord.document_date.desc().nullslast(),
            MedicalRecord.id.desc()
        )
        .limit(5)
        .all()
    )

    # Most recent prescription(s) surfaced separately
    recent_prescriptions = (
        MedicalRecord.query
        .filter_by(patient_id=u.id, document_type="prescription", is_deleted=False)
        .order_by(MedicalRecord.document_date.desc().nullslast())
        .limit(3)
        .all()
    )

    return jsonify(
        # Critical clinical fields
        blood_group=_field(u.blood_group, "patient-reported"),
        allergies=_field(u.allergies, "patient-reported"),
        conditions=_field(u.conditions, "patient-reported"),
        current_medicines=_field(u.current_medicines, "patient-reported"),

        # Emergency contact
        emergency_contact={
            "name": u.emergency_contact_name,
            "phone": u.emergency_contact_phone,
            "relation": u.emergency_contact_relation,
            "status": "present" if u.emergency_contact_phone else "missing",
        },

        # Supplementary recent documents
        recent_records=[r.to_dict() for r in recent_records],
        recent_prescriptions=[r.to_dict() for r in recent_prescriptions],

        # Patient identity (quick reference for clinician)
        patient={
            "name": u.full_name,
            "age": u.age,
            "gender": u.gender,
        },

        # Mandatory disclaimer — must be displayed prominently in the UI
        disclaimer=(
            "⚠️  All information is patient-reported and has not been independently verified "
            "by a clinician. Use as a starting point only. Always confirm critical details "
            "(allergies, medications, blood group) directly with the patient where possible."
        ),
    ), 200
