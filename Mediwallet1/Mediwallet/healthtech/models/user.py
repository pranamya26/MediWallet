from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


class User(UserMixin, db.Model):
    """
    Core user / patient account.
    Stores both authentication credentials and the medical profile
    (blood group, allergies, conditions, current medicines, emergency contact).
    """

    __tablename__ = "users"

    # ── Identity ──────────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # ── Personal information ──────────────────────────────────────────────────
    full_name = db.Column(db.String(150), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)      # male / female / other / prefer-not-to-say
    phone = db.Column(db.String(20), nullable=True)

    # ── Medical profile (patient-reported) ────────────────────────────────────
    blood_group = db.Column(db.String(10), nullable=True)          # e.g. "B+"
    allergies = db.Column(db.Text, nullable=True)                  # free text or comma-separated
    conditions = db.Column(db.Text, nullable=True)                 # existing diseases
    current_medicines = db.Column(db.Text, nullable=True)          # current medications + doses

    # ── Emergency contact ─────────────────────────────────────────────────────
    emergency_contact_name = db.Column(db.String(150), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    emergency_contact_relation = db.Column(db.String(50), nullable=True)  # e.g. spouse, parent

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────────────────────
    records = db.relationship(
        "MedicalRecord", backref="patient",
        lazy="dynamic", cascade="all, delete-orphan"
    )
    share_permissions = db.relationship(
        "SharePermission", backref="patient",
        lazy="dynamic", cascade="all, delete-orphan"
    )

    # ── Auth helpers ──────────────────────────────────────────────────────────
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # ── Age helper ────────────────────────────────────────────────────────────
    @property
    def age(self) -> int | None:
        if not self.date_of_birth:
            return None
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    # ── Serialisation ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "age": self.age,
            "gender": self.gender,
            "phone": self.phone,
            # Medical
            "blood_group": self.blood_group,
            "allergies": self.allergies,
            "conditions": self.conditions,
            "current_medicines": self.current_medicines,
            # Emergency
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "emergency_contact_relation": self.emergency_contact_relation,
            # Meta
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
