import os
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user
from models import db
from models.medical_record import MedicalRecord
from services.file_service import save_upload
from services.ocr_service import extract_text_from_file
from services.history_service import find_similar_tests, get_medicine_timeline
from services.categorization_service import (
    categorize_record as classify_health_category,
    get_all_categories_summary,
    VALID_HEALTH_CATEGORIES,
)

records_bp = Blueprint("records", __name__, url_prefix="/api/records")

VALID_DOC_TYPES = {"prescription", "blood_test", "scan", "discharge", "diagnosis", "other"}


# ── Upload ────────────────────────────────────────────────────────────────────

@records_bp.post("/upload")
@login_required
def upload_records():
    """
    Accept one or more files plus optional metadata.
    Form fields:  files (multipart, one or many)
                  document_type, document_date, hospital, doctor, notes
    Returns a list of results — one entry per file, success or error.
    """
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify(error="No files provided"), 400

    meta = request.form
    doc_type = meta.get("document_type", "other")
    if doc_type not in VALID_DOC_TYPES:
        doc_type = "other"

    results = []
    upload_folder = current_app.config["UPLOAD_FOLDER"]

    for file in files:
        if not file or file.filename == "":
            continue

        # ── Save to disk ──────────────────────────────────────────────────────
        try:
            stored_name, mime_type, original_name = save_upload(file, upload_folder)
        except ValueError as exc:
            results.append({"filename": file.filename, "error": str(exc)})
            continue

        # ── Create DB row ─────────────────────────────────────────────────────
        record = MedicalRecord(
            patient_id=current_user.id,
            stored_filename=stored_name,
            original_filename=original_name,
            mime_type=mime_type,
            document_type=doc_type,
            document_date=meta.get("document_date"),
            hospital=meta.get("hospital"),
            doctor=meta.get("doctor"),
            notes=meta.get("notes"),
            extraction_status="pending",
        )
        db.session.add(record)
        db.session.flush()          # obtain record.id before commit

        # ── OCR / text extraction (synchronous; move to a task queue for prod) ─
        filepath = os.path.join(upload_folder, stored_name)
        try:
            text = extract_text_from_file(filepath, mime_type)
            record.extracted_text = text
            record.extraction_status = "done"
        except Exception as exc:
            record.extraction_status = "failed"
            record.extracted_text = f"[Extraction error: {exc}]"

        # ── Health folder (created from user input) ───────────────────────────
        user_folder = (meta.get("folder_name") or meta.get("folder") or meta.get("health_category") or "").strip()
        if not user_folder:
            # Fallback if user left blank
            try:
                cat_result = classify_health_category(
                    text=record.extracted_text or "",
                    filename=original_name,
                    notes=meta.get("notes", ""),
                    doc_type=doc_type,
                    hospital=meta.get("hospital", ""),
                    doctor=meta.get("doctor", ""),
                )
                user_folder = cat_result["label"]
            except Exception:
                user_folder = "General Health"

        record.health_category = user_folder

        db.session.commit()
        results.append({"filename": original_name, "record": record.to_dict(include_text=False)})

    return jsonify(results=results), 201


# ── List / search ─────────────────────────────────────────────────────────────

@records_bp.get("/")
@login_required
def list_records():
    """
    Return the patient's records.
    Query params:
      type   – filter by document_type
      search – substring match on filename, hospital, doctor, or date
    Response includes a flat list and a grouped dict keyed by document_type.
    """
    q = MedicalRecord.query.filter_by(patient_id=current_user.id, is_deleted=False)

    doc_type = request.args.get("type", "").strip()
    if doc_type and doc_type in VALID_DOC_TYPES:
        q = q.filter_by(document_type=doc_type)

    search = request.args.get("search", "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(
            db.or_(
                MedicalRecord.original_filename.ilike(like),
                MedicalRecord.hospital.ilike(like),
                MedicalRecord.doctor.ilike(like),
                MedicalRecord.document_date.ilike(like),
                MedicalRecord.notes.ilike(like),
            )
        )

    records = q.order_by(
        MedicalRecord.document_date.desc().nullslast(),
        MedicalRecord.upload_timestamp.desc()
    ).all()

    # Group by type for the timeline view
    grouped: dict[str, list] = {}
    for r in records:
        grouped.setdefault(r.document_type or "other", []).append(r.to_dict())

    return jsonify(records=[r.to_dict() for r in records], grouped=grouped, total=len(records)), 200


# ── Single record ─────────────────────────────────────────────────────────────

@records_bp.get("/<int:record_id>")
@login_required
def get_record(record_id):
    """
    Return a single record with full extracted text.
    Also returns a list of similar earlier tests to warn the clinician.
    """
    record = _own_record_or_404(record_id)
    similar = find_similar_tests(current_user.id, record)
    return jsonify(record=record.to_dict(include_text=True), similar_tests=similar), 200


# ── Download (secure — no public URL) ────────────────────────────────────────

@records_bp.get("/<int:record_id>/download")
@login_required
def download_record(record_id):
    """Stream the file to the authenticated patient only."""
    record = _own_record_or_404(record_id)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        record.stored_filename,
        as_attachment=True,
        download_name=record.original_filename,
    )


# ── Update (patient corrects OCR / edits metadata) ───────────────────────────

@records_bp.patch("/<int:record_id>")
@login_required
def update_record(record_id):
    """
    Partial update — patient can correct metadata or verify OCR text.
    Body may include: document_type, document_date, hospital, doctor,
                      notes, extracted_text, patient_verified, health_category
    """
    record = _own_record_or_404(record_id)
    data = request.get_json(silent=True) or {}

    editable = ["document_type", "document_date", "hospital", "doctor",
                "notes", "extracted_text", "patient_verified", "health_category"]
    for field in editable:
        if field in data:
            if field == "document_type" and data[field] not in VALID_DOC_TYPES:
                return jsonify(error=f"Invalid document_type. Choose from: {', '.join(VALID_DOC_TYPES)}"), 400
            if field == "health_category":
                val = str(data[field]).strip() if data.get(field) else "General Health"
                setattr(record, field, val)
            else:
                setattr(record, field, data[field])

    # If patient edits extracted_text, mark as verified
    if "extracted_text" in data:
        record.patient_verified = True

    db.session.commit()
    return jsonify(message="Record updated", record=record.to_dict(include_text=True)), 200


# ── Delete (soft) ─────────────────────────────────────────────────────────────

@records_bp.delete("/<int:record_id>")
@login_required
def delete_record(record_id):
    """Soft-delete a record (file stays on disk; patient can request cleanup later)."""
    record = _own_record_or_404(record_id)
    record.is_deleted = True
    db.session.commit()
    return jsonify(message="Record deleted"), 200


# ── Medicine timeline ─────────────────────────────────────────────────────────

@records_bp.get("/history/medicines")
@login_required
def medicine_history():
    """Return all prescription records in reverse-chronological order."""
    timeline = get_medicine_timeline(current_user.id)
    return jsonify(medicine_timeline=timeline, total=len(timeline)), 200


# ── Health Folders — User-defined folder views ────────────────────────────────

@records_bp.get("/health-folders")
@login_required
def list_health_folders():
    """
    Return all user-created health folders with the count of records in each folder.
    Folders are dynamically created from user inputs.
    """
    records = MedicalRecord.query.filter_by(
        patient_id=current_user.id, is_deleted=False
    ).order_by(
        MedicalRecord.document_date.desc().nullslast(),
        MedicalRecord.upload_timestamp.desc(),
    ).all()

    folder_counts: dict[str, int] = {}
    folder_records: dict[str, list] = {}
    for r in records:
        cat = (r.health_category or "General Health").strip()
        folder_counts[cat] = folder_counts.get(cat, 0) + 1
        folder_records.setdefault(cat, []).append(r.to_dict())

    folders = [
        {
            "key": name,
            "label": name,
            "count": count,
            "description": f"Folder containing {count} medical report{'s' if count != 1 else ''}"
        }
        for name, count in sorted(folder_counts.items(), key=lambda x: x[0].lower())
    ]

    return jsonify(
        folders=folders,
        folder_records=folder_records,
        total=len(records),
    ), 200


@records_bp.get("/health-folders/<path:category>")
@login_required
def get_health_folder(category):
    """Return all records in a specific user-created health folder."""
    category = category.strip()
    records = MedicalRecord.query.filter_by(
        patient_id=current_user.id,
        is_deleted=False,
    ).filter(
        MedicalRecord.health_category.ilike(category)
    ).order_by(
        MedicalRecord.document_date.desc().nullslast(),
        MedicalRecord.upload_timestamp.desc(),
    ).all()

    return jsonify(
        category={"key": category, "label": category, "description": f"Folder containing {len(records)} reports"},
        records=[r.to_dict() for r in records],
        total=len(records),
    ), 200


@records_bp.get("/folders/names")
@login_required
def list_folder_names():
    """Return distinct folder names previously created by this user."""
    records = MedicalRecord.query.filter_by(
        patient_id=current_user.id, is_deleted=False
    ).all()
    names = sorted(list(set((r.health_category or "General Health").strip() for r in records if r.health_category)))
    return jsonify(folders=names), 200


@records_bp.post("/<int:record_id>/recategorize")
@login_required
def recategorize_record(record_id):
    """Re-run the auto-categorization on a single record."""
    record = _own_record_or_404(record_id)

    cat_result = classify_health_category(
        text=record.extracted_text or "",
        filename=record.original_filename or "",
        notes=record.notes or "",
        doc_type=record.document_type or "",
        hospital=record.hospital or "",
        doctor=record.doctor or "",
    )
    record.health_category = cat_result["category"]
    db.session.commit()

    return jsonify(
        message="Record recategorized",
        category=cat_result["category"],
        label=cat_result["label"],
        confidence=cat_result["confidence"],
        matched_terms=cat_result["matched_terms"],
        record=record.to_dict(include_text=False),
    ), 200


# ── Helper ────────────────────────────────────────────────────────────────────

def _own_record_or_404(record_id: int) -> MedicalRecord:
    return MedicalRecord.query.filter_by(
        id=record_id, patient_id=current_user.id, is_deleted=False
    ).first_or_404()
