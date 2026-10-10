"""
History service — duplicate-test detection and medicine timeline.

IMPORTANT: This service emits warnings to help clinicians review prior results.
It does NOT instruct patients to skip tests or change medications.
All warnings are advisory only.
"""

from __future__ import annotations

from models.medical_record import MedicalRecord

# ── Type groupings for "similar test" matching ────────────────────────────────
# Records with the same document_type are considered potentially duplicated.
# Extend this dict if you introduce more granular sub-types in the future.
_SIMILAR_TYPES: dict[str, list[str]] = {
    "blood_test":   ["blood_test"],
    "scan":         ["scan"],
    "prescription": ["prescription"],
    "discharge":    ["discharge"],
    "diagnosis":    ["diagnosis"],
    "other":        ["other"],
}

_WARNING_TEMPLATES: dict[str, str] = {
    "blood_test": (
        "A similar blood test ({filename}) was recorded on {date}. "
        "Please review the earlier result before ordering a new test."
    ),
    "scan": (
        "A prior scan ({filename}) was recorded on {date}. "
        "Consider reviewing it before requesting another imaging study."
    ),
    "prescription": (
        "A previous prescription ({filename}) from {date} is on file. "
        "Check for overlapping or interacting medications."
    ),
    "discharge": (
        "A discharge summary ({filename}) from {date} exists. "
        "It may contain relevant diagnoses or treatment notes."
    ),
    "diagnosis": (
        "An earlier diagnosis record ({filename}) from {date} is available. "
        "Please review it before forming a new assessment."
    ),
    "other": (
        "A similar document ({filename}) from {date} was previously uploaded."
    ),
}


# ── Public API ────────────────────────────────────────────────────────────────

def find_similar_tests(patient_id: int, record: MedicalRecord) -> list[dict]:
    """
    Find earlier records of the same document type for the same patient.

    Returns a list of dicts — each includes a human-readable warning string.
    The warning is advisory: clinicians should review, not blindly skip, tests.

    Parameters
    ----------
    patient_id : the owning patient's ID
    record     : the current record being viewed (excluded from results)
    """
    if not record.document_type:
        return []

    similar_types = _SIMILAR_TYPES.get(record.document_type, [record.document_type])

    earlier = (
        MedicalRecord.query
        .filter(
            MedicalRecord.patient_id == patient_id,
            MedicalRecord.id != record.id,
            MedicalRecord.document_type.in_(similar_types),
            MedicalRecord.is_deleted == False,
        )
        .order_by(MedicalRecord.document_date.desc().nullslast())
        .limit(5)
        .all()
    )

    results: list[dict] = []
    template = _WARNING_TEMPLATES.get(record.document_type, _WARNING_TEMPLATES["other"])

    for r in earlier:
        warning = template.format(
            filename=r.original_filename or "unnamed document",
            date=r.document_date or "an earlier date",
        )
        results.append({
            "id": r.id,
            "original_filename": r.original_filename,
            "document_date": r.document_date,
            "document_type": r.document_type,
            "hospital": r.hospital,
            "doctor": r.doctor,
            "warning": warning,
            "advisory_note": (
                "This is a system-generated notice. "
                "Clinical decisions should always be made by a qualified healthcare professional."
            ),
        })

    return results


def get_medicine_timeline(patient_id: int) -> list[dict]:
    """
    Return all prescription records in reverse-chronological order,
    with a short text preview of the extracted content.

    Used to show a patient's full medication history to a reviewing clinician.
    """
    records = (
        MedicalRecord.query
        .filter_by(patient_id=patient_id, document_type="prescription", is_deleted=False)
        .order_by(MedicalRecord.document_date.desc().nullslast())
        .all()
    )

    return [
        {
            "id": r.id,
            "original_filename": r.original_filename,
            "document_date": r.document_date,
            "doctor": r.doctor,
            "hospital": r.hospital,
            "patient_verified": r.patient_verified,
            # Limit preview to avoid sending huge payloads in the list view
            "extracted_text_preview": (r.extracted_text or "")[:400].strip() or None,
            "upload_timestamp": r.upload_timestamp.isoformat(),
        }
        for r in records
    ]


def get_full_timeline(patient_id: int) -> dict[str, list[dict]]:
    """
    Return ALL non-deleted records grouped by document_type,
    sorted by document_date descending within each group.
    Useful for rendering the complete medical history timeline.
    """
    records = (
        MedicalRecord.query
        .filter_by(patient_id=patient_id, is_deleted=False)
        .order_by(MedicalRecord.document_date.desc().nullslast(), MedicalRecord.upload_timestamp.desc())
        .all()
    )

    grouped: dict[str, list[dict]] = {}
    for r in records:
        key = r.document_type or "other"
        grouped.setdefault(key, []).append(r.to_dict())

    return grouped
