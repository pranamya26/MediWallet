"""
Auth route tests — registration, login, logout, /me, change-password.
Run with:  pytest tests/test_auth.py -v
"""

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register(client, email="alice@test.com", password="securepass1", name="Alice"):
    return client.post("/api/auth/register", json={
        "email": email, "password": password, "full_name": name
    })


def _login(client, email="alice@test.com", password="securepass1"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ── Registration ──────────────────────────────────────────────────────────────

class TestRegister:
    def test_success(self, client):
        rv = _register(client)
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["user"]["email"] == "alice@test.com"
        assert data["user"]["full_name"] == "Alice"
        assert "password_hash" not in data["user"]

    def test_duplicate_email(self, client):
        _register(client)
        rv = _register(client)
        assert rv.status_code == 409
        assert "already exists" in rv.get_json()["error"]

    def test_missing_email(self, client):
        rv = client.post("/api/auth/register", json={"password": "abc12345", "full_name": "X"})
        assert rv.status_code == 400

    def test_missing_name(self, client):
        rv = client.post("/api/auth/register", json={"email": "x@x.com", "password": "abc12345"})
        assert rv.status_code == 400

    def test_short_password(self, client):
        rv = client.post("/api/auth/register", json={
            "email": "x@x.com", "password": "123", "full_name": "X"
        })
        assert rv.status_code == 400
        assert "8 characters" in rv.get_json()["error"]

    def test_invalid_email_format(self, client):
        rv = client.post("/api/auth/register", json={
            "email": "notanemail", "password": "abc12345", "full_name": "X"
        })
        assert rv.status_code == 400


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_success(self, client):
        _register(client)
        rv = _login(client)
        assert rv.status_code == 200
        assert rv.get_json()["user"]["email"] == "alice@test.com"

    def test_wrong_password(self, client):
        _register(client)
        rv = client.post("/api/auth/login", json={"email": "alice@test.com", "password": "wrongpass"})
        assert rv.status_code == 401

    def test_unknown_email(self, client):
        rv = client.post("/api/auth/login", json={"email": "ghost@x.com", "password": "anything"})
        assert rv.status_code == 401

    def test_missing_fields(self, client):
        rv = client.post("/api/auth/login", json={"email": "alice@test.com"})
        assert rv.status_code == 400


# ── /me ───────────────────────────────────────────────────────────────────────

class TestMe:
    def test_authenticated(self, client):
        _register(client)
        rv = client.get("/api/auth/me")
        assert rv.status_code == 200

    def test_unauthenticated(self, client):
        rv = client.get("/api/auth/me")
        assert rv.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

class TestLogout:
    def test_success(self, client):
        _register(client)
        rv = client.post("/api/auth/logout")
        assert rv.status_code == 200

    def test_unauthenticated(self, client):
        rv = client.post("/api/auth/logout")
        assert rv.status_code == 401


# ── Change password ───────────────────────────────────────────────────────────

class TestChangePassword:
    def test_success(self, client):
        _register(client)
        rv = client.post("/api/auth/change-password", json={
            "current_password": "securepass1",
            "new_password": "newpassword99",
        })
        assert rv.status_code == 200

        # Old password should no longer work
        client.post("/api/auth/logout")
        rv = _login(client, password="securepass1")
        assert rv.status_code == 401

        # New password must work
        rv = _login(client, password="newpassword99")
        assert rv.status_code == 200

    def test_wrong_current_password(self, client):
        _register(client)
        rv = client.post("/api/auth/change-password", json={
            "current_password": "wrong",
            "new_password": "newpass123",
        })
        assert rv.status_code == 401

    def test_short_new_password(self, client):
        _register(client)
        rv = client.post("/api/auth/change-password", json={
            "current_password": "securepass1",
            "new_password": "short",
        })
        assert rv.status_code == 400
