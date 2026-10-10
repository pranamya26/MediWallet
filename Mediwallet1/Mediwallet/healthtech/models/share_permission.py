import secrets
from datetime import datetime
from models import db


class SharePermission(db.Model):
    """
    A time-limited, revocable share token that gives a doctor read-only
    access to a subset (or all) of a patient's medical records.

    The token is embedded in a URL and/or QR code.  No doctor account is
    required — anyone with the link can view the records until expiry or
    revocation, so patients must treat tokens like passwords.
    """

    __tablename__ = "share_permissions"

    # ── Primary key / ownership ───────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # ── Token ─────────────────────────────────────────────────────────────────
    token = db.Column(
        db.String(64), unique=True, nullable=False,
        default=lambda: secrets.token_urlsafe(32)
    )

    # ── Scope — which records are visible ─────────────────────────────────────
    record_ids = db.Column(db.Text, nullable=True)
    # "all"  → every non-deleted record
    # "1,2,3" → comma-separated record IDs

    # ── Optional context stored for the patient's reference ───────────────────
    doctor_name = db.Column(db.String(150), nullable=True)
    doctor_note = db.Column(db.Text, nullable=True)           # e.g. "shared for cardiology consult"

    # ── Access control ────────────────────────────────────────────────────────
    expires_at = db.Column(db.DateTime, nullable=False)
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)

    # ── Access audit log ──────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed_at = db.Column(db.DateTime, nullable=True)
    access_count = db.Column(db.Integer, default=0, nullable=False)

    # ── Computed property ─────────────────────────────────────────────────────
    @property
    def is_valid(self) -> bool:
        """True if the link has not been revoked and has not yet expired."""
        return not self.is_revoked and datetime.utcnow() < self.expires_at

    @property
    def status(self) -> str:
        if self.is_revoked:
            return "revoked"
        if datetime.utcnow() >= self.expires_at:
            return "expired"
        return "active"

    # ── Serialisation ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "token": self.token,
            "record_ids": self.record_ids,
            "doctor_name": self.doctor_name,
            "doctor_note": self.doctor_note,
            "expires_at": self.expires_at.isoformat(),
            "is_revoked": self.is_revoked,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "access_count": self.access_count,
        }

    def __repr__(self) -> str:
        return f"<SharePermission id={self.id} patient={self.patient_id} status={self.status}>"
