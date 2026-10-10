from datetime import datetime
from models import db


class MedicalRecord(db.Model):
    """
    A single uploaded medical document (PDF, DOCX, or image).
    Stores the file on disk under a UUID-based name and captures
    patient-supplied metadata plus any OCR-extracted text.
    """

    __tablename__ = "medical_records"

    # ── Primary key / ownership ───────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # ── Stored file ───────────────────────────────────────────────────────────
    stored_filename = db.Column(db.String(255), nullable=False)   # UUID hex + ext — not user-controlled
    original_filename = db.Column(db.String(255), nullable=True)  # shown in the UI
    mime_type = db.Column(db.String(120), nullable=True)

    # ── Patient-supplied metadata ─────────────────────────────────────────────
    document_type = db.Column(db.String(50), nullable=True)
    # prescription | blood_test | scan | discharge | diagnosis | other
    health_category = db.Column(db.String(50), default="general_health", nullable=True)
    # diabetes_sugar | blood_pressure | heart_health | thyroid | kidney | liver | general_health
    document_date = db.Column(db.String(20), nullable=True)       # ISO date string YYYY-MM-DD
    hospital = db.Column(db.String(150), nullable=True)
    doctor = db.Column(db.String(150), nullable=True)
    notes = db.Column(db.Text, nullable=True)                     # optional patient note

    # ── OCR / text extraction ─────────────────────────────────────────────────
    extracted_text = db.Column(db.Text, nullable=True)
    extraction_status = db.Column(db.String(20), default="pending")
    # pending | done | failed
    patient_verified = db.Column(db.Boolean, default=False)       # patient has reviewed extracted text

    # ── Optional AI-generated summary ─────────────────────────────────────────
    ai_summary = db.Column(db.Text, nullable=True)
    # Clearly labelled as AI assistance — not a medical diagnosis

    # ── Soft-delete flag ──────────────────────────────────────────────────────
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Serialisation ─────────────────────────────────────────────────────────
    def to_dict(self, include_text: bool = False) -> dict:
        d = {
            "id": self.id,
            "patient_id": self.patient_id,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "document_type": self.document_type,
            "health_category": self.health_category or "general_health",
            "document_date": self.document_date,
            "hospital": self.hospital,
            "doctor": self.doctor,
            "notes": self.notes,
            "extraction_status": self.extraction_status,
            "patient_verified": self.patient_verified,
            "ai_summary": self.ai_summary,
            "upload_timestamp": self.upload_timestamp.isoformat(),
        }
        if include_text:
            d["extracted_text"] = self.extracted_text
        return d

    def __repr__(self) -> str:
        return f"<MedicalRecord id={self.id} type={self.document_type} patient={self.patient_id}>"
