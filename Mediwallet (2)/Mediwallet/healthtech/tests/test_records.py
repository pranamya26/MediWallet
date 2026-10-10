"""
Records route tests — upload, list, filter, search, update, delete, download.
Run with:  pytest tests/test_records.py -v
"""

import io
import pytest
from app import create_app
from models import db as _db
from config import TestingConfig


@pytest.fixture(scope="function")
def app(tmp_path):
    TestingConfig.UPLOAD_FOLDER = str(tmp_path / "uploads")
    application = create_app(TestingConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A test client that is already registered and logged in."""
    client.post("/api/auth/register", json={
        "email": "patient@test.com",
        "password": "testpass99",
        "full_name": "Test Patient",
    })
    client.post("/api/auth/login", json={"email": "patient@test.com", "password": "testpass99"})
    return client


# ── Helpers ───────────────────────────────────────────────────────────────────

def _upload(client, filename="report.pdf", content=b"%PDF-1.4 fake", doc_type="blood_test", **extra):
    data = {
        "files": (io.BytesIO(content), filename),
        "document_type": doc_type,
    }
    data.update(extra)
    return client.post("/api/records/upload", data=data, content_type="multipart/form-data")


# ── Upload ────────────────────────────────────────────────────────────────────

class TestUpload:
    def test_pdf_upload_success(self, auth_client):
        rv = _upload(auth_client)
        assert rv.status_code == 201
        results = rv.get_json()["results"]
        assert len(results) == 1
        assert results[0]["filename"] == "report.pdf"
        assert "error" not in results[0]

    def test_image_upload_success(self, auth_client):
        rv = _upload(auth_client, filename="xray.jpg", content=b"\xff\xd8\xff fake jpeg")
        assert rv.status_code == 201

    def test_invalid_extension_rejected(self, auth_client):
        rv = _upload(auth_client, filename="script.exe", content=b"malicious")
        assert rv.status_code == 201             # endpoint returns 201 with per-file errors
        result = rv.get_json()["results"][0]
        assert "error" in result

    def test_no_file_returns_400(self, auth_client):
        rv = auth_client.post("/api/records/upload", data={}, content_type="multipart/form-data")
        assert rv.status_code == 400

    def test_unauthenticated_upload_rejected(self, client):
        rv = _upload(client)
        assert rv.status_code == 401

    def test_metadata_stored(self, auth_client):
        rv = _upload(
            auth_client,
            doc_type="prescription",
            document_date="2024-06-01",
            hospital="City Hospital",
            doctor="Dr. Smith",
        )
        record = rv.get_json()["results"][0]["record"]
        assert record["document_type"] == "prescription"
        assert record["document_date"] == "2024-06-01"
        assert record["hospital"] == "City Hospital"
        assert record["doctor"] == "Dr. Smith"

    def test_invalid_doc_type_defaults_to_other(self, auth_client):
        rv = _upload(auth_client, doc_type="bogus_type")
        record = rv.get_json()["results"][0]["record"]
        assert record["document_type"] == "other"


# ── List and filter ───────────────────────────────────────────────────────────

class TestListRecords:
    def test_empty_list(self, auth_client):
        rv = auth_client.get("/api/records/")
        assert rv.status_code == 200
        assert rv.get_json()["records"] == []

    def test_records_appear_after_upload(self, auth_client):
        _upload(auth_client)
        rv = auth_client.get("/api/records/")
        assert len(rv.get_json()["records"]) == 1

    def test_filter_by_type(self, auth_client):
        _upload(auth_client, doc_type="prescription")
        _upload(auth_client, doc_type="blood_test", filename="blood.pdf")
        rv = auth_client.get("/api/records/?type=prescription")
        records = rv.get_json()["records"]
        assert all(r["document_type"] == "prescription" for r in records)
        assert len(records) == 1

    def test_search_by_hospital(self, auth_client):
        _upload(auth_client, hospital="Apollo", doc_type="scan", filename="scan.pdf")
        _upload(auth_client, hospital="Fortis", doc_type="scan", filename="scan2.pdf")
        rv = auth_client.get("/api/records/?search=Apollo")
        records = rv.get_json()["records"]
        assert len(records) == 1
        assert records[0]["hospital"] == "Apollo"

    def test_grouped_in_response(self, auth_client):
        _upload(auth_client, doc_type="prescription")
        _upload(auth_client, doc_type="blood_test", filename="b.pdf")
        rv = auth_client.get("/api/records/")
        grouped = rv.get_json()["grouped"]
        assert "prescription" in grouped
        assert "blood_test" in grouped

    def test_unauthenticated_list_rejected(self, client):
        rv = client.get("/api/records/")
        assert rv.status_code == 401


# ── Single record ─────────────────────────────────────────────────────────────

class TestGetRecord:
    def test_get_own_record(self, auth_client):
        rv = _upload(auth_client)
        record_id = rv.get_json()["results"][0]["record"]["id"]
        rv = auth_client.get(f"/api/records/{record_id}")
        assert rv.status_code == 200
        assert rv.get_json()["record"]["id"] == record_id

    def test_get_nonexistent_returns_404(self, auth_client):
        rv = auth_client.get("/api/records/99999")
        assert rv.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

class TestUpdateRecord:
    def test_update_metadata(self, auth_client):
        rv = _upload(auth_client)
        record_id = rv.get_json()["results"][0]["record"]["id"]
        rv = auth_client.patch(f"/api/records/{record_id}", json={
            "hospital": "Updated Hospital",
            "doctor": "Dr. New",
        })
        assert rv.status_code == 200
        r = rv.get_json()["record"]
        assert r["hospital"] == "Updated Hospital"

    def test_verify_extracted_text(self, auth_client):
        rv = _upload(auth_client)
        record_id = rv.get_json()["results"][0]["record"]["id"]
        rv = auth_client.patch(f"/api/records/{record_id}", json={
            "extracted_text": "Corrected text by patient",
        })
        assert rv.status_code == 200
        assert rv.get_json()["record"]["patient_verified"] is True


# ── Delete ────────────────────────────────────────────────────────────────────

class TestDeleteRecord:
    def test_soft_delete(self, auth_client):
        rv = _upload(auth_client)
        record_id = rv.get_json()["results"][0]["record"]["id"]

        rv = auth_client.delete(f"/api/records/{record_id}")
        assert rv.status_code == 200

        rv = auth_client.get("/api/records/")
        ids = [r["id"] for r in rv.get_json()["records"]]
        assert record_id not in ids

    def test_cannot_delete_others_record(self, app, client):
        # Register second user
        client.post("/api/auth/register", json={
            "email": "other@test.com", "password": "otherpass9", "full_name": "Other"
        })
        client.post("/api/auth/login", json={"email": "other@test.com", "password": "otherpass9"})
        rv = _upload(client)
        record_id = rv.get_json()["results"][0]["record"]["id"]
        client.post("/api/auth/logout")

        # Log in as first user and try to delete other's record
        client.post("/api/auth/register", json={
            "email": "me@test.com", "password": "mypass1234", "full_name": "Me"
        })
        client.post("/api/auth/login", json={"email": "me@test.com", "password": "mypass1234"})
        rv = client.delete(f"/api/records/{record_id}")
        assert rv.status_code == 404        # not found for this user


# ── Medicine history ──────────────────────────────────────────────────────────

class TestMedicineHistory:
    def test_returns_only_prescriptions(self, auth_client):
        _upload(auth_client, doc_type="prescription", filename="rx1.pdf")
        _upload(auth_client, doc_type="blood_test", filename="blood.pdf")
        rv = auth_client.get("/api/records/history/medicines")
        assert rv.status_code == 200
        timeline = rv.get_json()["medicine_timeline"]
        assert len(timeline) == 1
        assert timeline[0]["original_filename"] == "rx1.pdf"
