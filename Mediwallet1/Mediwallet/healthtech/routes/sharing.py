import io
import os
import base64
import socket
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from models import db
from models.share_permission import SharePermission
from models.medical_record import MedicalRecord

sharing_bp = Blueprint("sharing", __name__, url_prefix="/api/share")


def _get_local_ip() -> str:
    """Best-effort discovery of local LAN IP address for QR codes."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        # Does not actually make a connection
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_public_base_url() -> str:
    """
    Resolve base URL for share links and QR codes:
    1. If PUBLIC_BASE_URL / APP_BASE_URL is set in config, use it.
    2. Else if request host is 'localhost' or '127.0.0.1', replace with machine LAN IP so
       mobile phones scanning the QR code on the same Wi-Fi can reach it.
    3. Else fallback to request.host_url.
    """
    configured = current_app.config.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured

    host = request.host.split(":")[0].lower()
    port = request.host.split(":")[1] if ":" in request.host else ""
    port_suffix = f":{port}" if port else ""

    if host in ("localhost", "127.0.0.1"):
        lan_ip = _get_local_ip()
        return f"{request.scheme}://{lan_ip}{port_suffix}"

    return request.host_url.rstrip("/")


# ── Create a share link ───────────────────────────────────────────────────────

@sharing_bp.post("/create")
@login_required
def create_share():
    """
    Generate a time-limited share link (and QR code) for a set of records.
    Body:
      record_ids   – list of int IDs, or the string "all" (default: "all")
      expiry_hours – 1–720  (default: 24)
      doctor_name  – optional label for the patient's reference
      doctor_note  – optional note (e.g. "cardiology consult")
    """
    data = request.get_json(silent=True) or {}

    # ── Resolve record scope ──────────────────────────────────────────────────
    record_ids_raw = data.get("record_ids", "all")
    if isinstance(record_ids_raw, list):
        # Validate that all IDs belong to this patient
        ids = [int(i) for i in record_ids_raw if str(i).isdigit()]
        owned = (MedicalRecord.query
                 .filter(MedicalRecord.id.in_(ids),
                         MedicalRecord.patient_id == current_user.id,
                         MedicalRecord.is_deleted == False)
                 .with_entities(MedicalRecord.id).all())
        valid_ids = [r.id for r in owned]
        if not valid_ids:
            return jsonify(error="None of the specified record IDs are valid"), 400
        record_ids_str = ",".join(str(i) for i in valid_ids)
    else:
        record_ids_str = "all"

    # ── Expiry ────────────────────────────────────────────────────────────────
    max_hours = current_app.config.get("MAX_SHARE_EXPIRY_HOURS", 720)
    expiry_hours = int(data.get("expiry_hours", current_app.config.get("DEFAULT_SHARE_EXPIRY_HOURS", 24)))
    expiry_hours = max(1, min(expiry_hours, max_hours))

    # ── Persist ───────────────────────────────────────────────────────────────
    perm = SharePermission(
        patient_id=current_user.id,
        record_ids=record_ids_str,
        doctor_name=data.get("doctor_name"),
        doctor_note=data.get("doctor_note"),
        expires_at=datetime.utcnow() + timedelta(hours=expiry_hours),
    )
    db.session.add(perm)
    db.session.commit()

    base_url = get_public_base_url()
    share_url = f"{base_url}/shared/{perm.token}"

    # ── QR code with complete public-facing URL ───────────────────────────────
    qr_b64 = _make_qr(share_url)

    return jsonify(
        share_url=share_url,
        token=perm.token,
        expires_at=perm.expires_at.isoformat(),
        expiry_hours=expiry_hours,
        qr_code=f"data:image/png;base64,{qr_b64}",
        share=perm.to_dict(),
    ), 201


# ── View shared records (no auth required — token acts as the credential) ─────

@sharing_bp.get("/view/<token>")
def view_shared(token):
    """
    Public endpoint accessed by the doctor via the share link.
    No login needed — the token IS the access control.
    """
    perm = SharePermission.query.filter_by(token=token).first_or_404()

    if not perm.is_valid:
        reason = "revoked" if perm.is_revoked else "expired"
        return jsonify(error=f"This link has been {reason} and is no longer accessible"), 403

    # Audit
    perm.last_accessed_at = datetime.utcnow()
    perm.access_count += 1
    db.session.commit()

    # Fetch the permitted records
    q = MedicalRecord.query.filter_by(patient_id=perm.patient_id, is_deleted=False)
    if perm.record_ids != "all":
        ids = [int(i) for i in perm.record_ids.split(",") if i.strip().isdigit()]
        q = q.filter(MedicalRecord.id.in_(ids))

    records = q.order_by(
        MedicalRecord.document_date.desc().nullslast(),
        MedicalRecord.upload_timestamp.desc()
    ).all()

    patient = perm.patient
    return jsonify(
        shared_by=patient.full_name,
        doctor_name=perm.doctor_name,
        doctor_note=perm.doctor_note,
        expires_at=perm.expires_at.isoformat(),
        access_count=perm.access_count,
        # Health summary fields authorized with patient consent
        health_summary={
            "blood_group": patient.blood_group,
            "allergies": patient.allergies,
            "conditions": patient.conditions,
            "current_medicines": patient.current_medicines,
            "emergency_contact": (
                f"{patient.emergency_contact_name} ({patient.emergency_contact_relation or 'Contact'}) · {patient.emergency_contact_phone}"
                if patient.emergency_contact_phone else None
            ),
            "age": patient.age,
            "gender": patient.gender,
        },
        records=[r.to_dict(include_text=True) for r in records],
        disclaimer=(
            "These records are shared directly by the patient for consultation purposes. "
            "All health summary items are patient-reported and have not been independently verified."
        ),
    ), 200


# ── Shared file download (token-gated, no patient login needed) ───────────────

@sharing_bp.get("/view/<token>/download/<int:record_id>")
def download_shared_record(token, record_id):
    """Download a specific record via a valid share token."""
    from flask import send_from_directory
    perm = SharePermission.query.filter_by(token=token).first_or_404()

    if not perm.is_valid:
        return jsonify(error="Link is expired or revoked"), 403

    # Ensure the record is within the permitted scope
    if perm.record_ids != "all":
        allowed = [int(i) for i in perm.record_ids.split(",") if i.strip().isdigit()]
        if record_id not in allowed:
            return jsonify(error="Record not included in this share link"), 403

    record = MedicalRecord.query.filter_by(
        id=record_id, patient_id=perm.patient_id, is_deleted=False
    ).first_or_404()

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        record.stored_filename,
        as_attachment=True,
        download_name=record.original_filename,
    )


# ── Patient: list all their share links ───────────────────────────────────────

@sharing_bp.get("/")
@login_required
def list_shares():
    """Return all share links created by the logged-in patient, newest first."""
    perms = (SharePermission.query
             .filter_by(patient_id=current_user.id)
             .order_by(SharePermission.created_at.desc())
             .all())
    return jsonify(shares=[p.to_dict() for p in perms], total=len(perms)), 200


# ── Revoke ────────────────────────────────────────────────────────────────────

@sharing_bp.delete("/<int:perm_id>/revoke")
@login_required
def revoke_share(perm_id):
    """Immediately invalidate a share link."""
    perm = SharePermission.query.filter_by(
        id=perm_id, patient_id=current_user.id
    ).first_or_404()

    if perm.is_revoked:
        return jsonify(message="Already revoked"), 200

    perm.is_revoked = True
    db.session.commit()
    return jsonify(message="Share link revoked successfully"), 200


# ── Access history for a specific share link ──────────────────────────────────

@sharing_bp.get("/<int:perm_id>/history")
@login_required
def share_history(perm_id):
    """Return access audit info for a specific share link."""
    perm = SharePermission.query.filter_by(
        id=perm_id, patient_id=current_user.id
    ).first_or_404()
    return jsonify(share=perm.to_dict()), 200


# ── Internal helper ───────────────────────────────────────────────────────────

def _make_qr(url: str) -> str:
    """Return a base64-encoded PNG QR code for the given URL."""
    try:
        import qrcode
        img = qrcode.make(url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        # qrcode not installed — return empty string; frontend can skip the QR
        return ""
