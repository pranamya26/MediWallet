"""
Tests for QR sharing, token-gated access, expiry, revocation, and security boundaries.
Run with:  pytest tests/test_sharing.py -v
"""

import io
from datetime import datetime, timedelta
import pytest
from app import create_app
from models import db as _db
from models.share_permission import SharePermission
from config import TestingConfig


@pytest.fixture(scope="function")
def app(tmp_path):
    TestingConfig.UPLOAD_FOLDER = str(tmp_path / "uploads")
    TestingConfig.PUBLIC_BASE_URL = "http://testserver.local:5000"
    application = create_app(TestingConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_patient(client):
    client.post("/api/auth/register", json={
        "email": "sarah@test.com",
        "password": "password1234",
        "full_name": "Sarah Connor",
    })
    client.post("/api/auth/login", json={"email": "sarah@test.com", "password": "password1234"})
    
    # Fill patient profile
    client.put("/api/profile/", json={
        "blood_group": "O+",
        "allergies": "Penicillin",
        "conditions": "Asthma",
        "current_medicines": "Albuterol inhaler",
        "emergency_contact_name": "John Connor",
        "emergency_contact_phone": "+1-555-0199",
        "emergency_contact_relation": "Son",
    })

    # Upload two records
    res1 = client.post("/api/records/upload", data={
        "files": (io.BytesIO(b"%PDF-1.4 report 1"), "blood_report.pdf"),
        "document_type": "blood_test",
        "hospital": "City Lab",
    }, content_type="multipart/form-data")
    rec1_id = res1.get_json()["results"][0]["record"]["id"]

    res2 = client.post("/api/records/upload", data={
        "files": (io.BytesIO(b"%PDF-1.4 report 2"), "prescription.pdf"),
        "document_type": "prescription",
        "hospital": "General Hospital",
    }, content_type="multipart/form-data")
    rec2_id = res2.get_json()["results"][0]["record"]["id"]

    return {
        "client": client,
        "rec1_id": rec1_id,
        "rec2_id": rec2_id,
    }


class TestQRSharing:
    def test_create_share_uses_configured_base_url_and_generates_qr(self, auth_patient):
        client = auth_patient["client"]
        rec1_id = auth_patient["rec1_id"]

        rv = client.post("/api/share/create", json={
            "record_ids": [rec1_id],
            "expiry_hours": 2,
            "doctor_name": "Dr. Silberman",
            "doctor_note": "Psychiatry consultation",
        })
        assert rv.status_code == 201
        data = rv.get_json()
        assert "token" in data
        assert len(data["token"]) >= 32
        assert data["share_url"].startswith("http://testserver.local:5000/shared/")
        assert data["share_url"].endswith(data["token"])
        assert data["qr_code"].startswith("data:image/png;base64,")

    def test_direct_shared_page_renders_without_login(self, auth_patient):
        client = auth_patient["client"]
        rec1_id = auth_patient["rec1_id"]

        rv = client.post("/api/share/create", json={"record_ids": [rec1_id]})
        token = rv.get_json()["token"]

        # Logout patient
        client.post("/api/auth/logout")

        # Open public web page /shared/<token> (no session)
        page_rv = client.get(f"/shared/{token}")
        assert page_rv.status_code == 200
        assert b"Shared Medical Records" in page_rv.data
        assert token.encode() in page_rv.data

    def test_shared_api_returns_only_authorized_records(self, auth_patient):
        client = auth_patient["client"]
        rec1_id = auth_patient["rec1_id"]
        rec2_id = auth_patient["rec2_id"]

        # Share ONLY record 1
        rv = client.post("/api/share/create", json={
            "record_ids": [rec1_id],
            "doctor_name": "Dr. Smith",
        })
        token = rv.get_json()["token"]

        # Logout patient
        client.post("/api/auth/logout")

        # Public API call by doctor / phone browser
        api_rv = client.get(f"/api/share/view/{token}")
        assert api_rv.status_code == 200
        view_data = api_rv.get_json()
        
        assert view_data["shared_by"] == "Sarah Connor"
        assert view_data["doctor_name"] == "Dr. Smith"
        assert view_data["health_summary"]["blood_group"] == "O+"
        assert view_data["health_summary"]["allergies"] == "Penicillin"

        # Check records visibility
        visible_ids = [r["id"] for r in view_data["records"]]
        assert rec1_id in visible_ids
        assert rec2_id not in visible_ids

        # Access count audit incremented
        assert view_data["access_count"] >= 1

    def test_authorized_download_allowed_unauthorized_blocked(self, auth_patient):
        client = auth_patient["client"]
        rec1_id = auth_patient["rec1_id"]
        rec2_id = auth_patient["rec2_id"]

        # Share only record 1
        rv = client.post("/api/share/create", json={"record_ids": [rec1_id]})
        token = rv.get_json()["token"]

        client.post("/api/auth/logout")

        # Authorized record download succeeds
        dl_rv = client.get(f"/api/share/view/{token}/download/{rec1_id}")
        assert dl_rv.status_code == 200

        # Attempting to download unauthorized record 2 is rejected
        dl_bad = client.get(f"/api/share/view/{token}/download/{rec2_id}")
        assert dl_bad.status_code == 403
        assert "not included" in dl_bad.get_json()["error"]

    def test_revocation_immediately_blocks_access(self, auth_patient, app):
        client = auth_patient["client"]
        rec1_id = auth_patient["rec1_id"]

        rv = client.post("/api/share/create", json={"record_ids": [rec1_id]})
        data = rv.get_json()
        token = data["token"]
        share_id = data["share"]["id"]

        # Revoke as patient
        revoke_rv = client.delete(f"/api/share/{share_id}/revoke")
        assert revoke_rv.status_code == 200

        client.post("/api/auth/logout")

        # Viewing revoked link is forbidden
        view_rv = client.get(f"/api/share/view/{token}")
        assert view_rv.status_code == 403
        assert "revoked" in view_rv.get_json()["error"]

        # Downloading via revoked link is forbidden
        dl_rv = client.get(f"/api/share/view/{token}/download/{rec1_id}")
        assert dl_rv.status_code == 403

    def test_expired_link_is_blocked(self, auth_patient, app):
        client = auth_patient["client"]
        rec1_id = auth_patient["rec1_id"]

        rv = client.post("/api/share/create", json={"record_ids": [rec1_id]})
        data = rv.get_json()
        token = data["token"]
        share_id = data["share"]["id"]

        # Manually backdate expiration in DB to simulate expired link
        with app.app_context():
            perm = SharePermission.query.get(share_id)
            perm.expires_at = datetime.utcnow() - timedelta(minutes=10)
            _db.session.commit()

        client.post("/api/auth/logout")

        view_rv = client.get(f"/api/share/view/{token}")
        assert view_rv.status_code == 403
        assert "expired" in view_rv.get_json()["error"]
