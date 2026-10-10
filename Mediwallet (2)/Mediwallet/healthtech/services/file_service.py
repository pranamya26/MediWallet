import os
import uuid
import mimetypes

from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

# ── Constants ─────────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}

# Map extensions to canonical MIME types for extra safety
EXT_TO_MIME: dict[str, str] = {
    ".pdf":  "application/pdf",
    ".doc":  "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
}

MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB


# ── Public API ────────────────────────────────────────────────────────────────

def save_upload(file: FileStorage, upload_folder: str) -> tuple[str, str, str]:
    """
    Validate and save an uploaded file to *upload_folder*.

    Returns
    -------
    stored_filename : str   UUID-based name on disk (no user input in path)
    mime_type       : str   Canonical MIME type inferred from extension
    original_name   : str   Safe version of the original filename (for display)

    Raises
    ------
    ValueError  if the file fails any validation check
    """
    original_name = secure_filename(file.filename or "")
    if not original_name:
        raise ValueError("Invalid or missing filename")

    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type '{ext}' is not allowed. "
            f"Accepted types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # ── Size check ────────────────────────────────────────────────────────────
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size == 0:
        raise ValueError("Uploaded file is empty")
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File exceeds the 16 MB size limit ({size // (1024*1024)} MB received)")

    # ── MIME type ─────────────────────────────────────────────────────────────
    # Prefer extension-derived MIME over browser-supplied content_type
    # (browsers can lie; the file extension is already validated above)
    mime_type = EXT_TO_MIME.get(ext) or mimetypes.guess_type(original_name)[0] or "application/octet-stream"

    # ── Save with UUID name ───────────────────────────────────────────────────
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(upload_folder, stored_name)
    os.makedirs(upload_folder, exist_ok=True)
    file.save(dest)

    return stored_name, mime_type, original_name


def delete_file(upload_folder: str, stored_filename: str) -> bool:
    """
    Remove a stored file from disk.
    Returns True if the file was deleted, False if it did not exist.
    """
    path = os.path.join(upload_folder, stored_filename)
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False
