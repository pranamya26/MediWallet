from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

pages_bp = Blueprint("pages", __name__)


def _patient_or_login():
    """Return redirect if the user is not logged in."""
    if not current_user.is_authenticated:
        return redirect(url_for("pages.login"))
    return None


# ── Public ────────────────────────────────────────────────────────────────────

@pages_bp.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    return redirect(url_for("pages.login"))


@pages_bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    return render_template("login.html")


@pages_bp.get("/register")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    return render_template("register.html")


# ── Public Direct Shared Record View (Accessed by QR Code Scan) ───────────────

@pages_bp.get("/shared/<token>")
def shared_record_view(token):
    """
    Direct public page opened when a clinician scans the patient's QR code.
    No login or account creation required — token acts as access authorization.
    """
    return render_template("shared_record.html", token=token)


# ── Legacy redirect ───────────────────────────────────────────────────────────

@pages_bp.get("/doctor")
@pages_bp.get("/doctor/view/<token>")
def doctor_redirect(token=None):
    """Redirect legacy doctor links to direct shared route or login."""
    if token:
        return redirect(url_for("pages.shared_record_view", token=token))
    return redirect(url_for("pages.login"))


# ── Protected patient pages ───────────────────────────────────────────────────

@pages_bp.get("/dashboard")
def dashboard():
    guard = _patient_or_login()
    if guard:
        return guard
    return render_template("dashboard.html")


@pages_bp.get("/profile")
def profile():
    guard = _patient_or_login()
    if guard:
        return guard
    return render_template("profile.html")


@pages_bp.get("/upload")
def upload():
    guard = _patient_or_login()
    if guard:
        return guard
    return render_template("upload.html")


@pages_bp.get("/history")
def history():
    guard = _patient_or_login()
    if guard:
        return guard
    return render_template("history.html")


@pages_bp.get("/share")
def share():
    guard = _patient_or_login()
    if guard:
        return guard
    return render_template("share.html")


@pages_bp.get("/emergency")
def emergency():
    guard = _patient_or_login()
    if guard:
        return guard
    return render_template("emergency.html")


@pages_bp.get("/privacy")
def privacy():
    guard = _patient_or_login()
    if guard:
        return guard
    return render_template("privacy.html")


@pages_bp.get("/folders")
def folders():
    guard = _patient_or_login()
    if guard:
        return guard
    return render_template("folders.html")
