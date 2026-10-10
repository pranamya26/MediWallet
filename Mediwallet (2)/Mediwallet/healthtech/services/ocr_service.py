"""
OCR and text-extraction service.

Handles three file families:
  • PDF  — extract embedded text layer (pdfplumber); fall back to OCR via PyMuPDF + Tesseract
  • DOCX — extract paragraph text (python-docx)
  • Image (JPG / PNG) — run Tesseract OCR via pytesseract

All heavy libraries are optional-imported with graceful fallback messages so the
app still starts even if Tesseract is not installed on the current machine.
"""

from __future__ import annotations

import os

# ── Optional dependency guards ────────────────────────────────────────────────

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False


def _configure_tesseract():
    """Ensure pytesseract points to a valid tesseract binary on Windows."""
    if not _OCR_AVAILABLE:
        return
    possible_paths = [
        os.environ.get("TESSERACT_CMD", ""),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for p in possible_paths:
        if p and os.path.isfile(p):
            pytesseract.pytesseract.tesseract_cmd = p
            break


_configure_tesseract()

try:
    import pdfplumber
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False

try:
    from docx import Document as _DocxDocument
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False


# ── Public entry point ────────────────────────────────────────────────────────

def extract_text_from_file(filepath: str, mime_type: str = "") -> str:
    """
    Extract readable text from a supported file.

    Parameters
    ----------
    filepath  : absolute path to the file on disk
    mime_type : MIME type hint (used only as a secondary signal)

    Returns
    -------
    Extracted text string (may be empty or contain a bracketed error note).
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        return _from_pdf(filepath)
    elif ext in (".docx", ".doc"):
        return _from_docx(filepath)
    elif ext in (".jpg", ".jpeg", ".png"):
        return _from_image(filepath)
    else:
        return f"[Unsupported file type: {ext}]"


# ── PDF extraction ────────────────────────────────────────────────────────────

def _from_pdf(filepath: str) -> str:
    if not _PDF_AVAILABLE:
        return "[PDF text extraction unavailable — install pdfplumber: pip install pdfplumber]"

    parts: list[str] = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
    except Exception as exc:
        return f"[pdfplumber error: {exc}]"

    full_text = "\n".join(parts).strip()

    # Scanned PDF (no text layer) — try OCR via PyMuPDF
    if not full_text:
        full_text = _ocr_pdf(filepath)

    return full_text or "[No readable text found in this PDF]"


def _ocr_pdf(filepath: str) -> str:
    """Render each PDF page as an image and run Tesseract on it."""
    if not _OCR_AVAILABLE:
        return "[OCR unavailable for scanned PDF — install pytesseract and Pillow]"

    _configure_tesseract()
    try:
        import fitz  # PyMuPDF — already in requirements.txt
        doc = fitz.open(filepath)
        texts: list[str] = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            texts.append(pytesseract.image_to_string(img))
        doc.close()
    except Exception as exc:
        return f"[PDF OCR error: {exc}]"

    return "\n".join(texts).strip()


# ── DOCX extraction ───────────────────────────────────────────────────────────

def _from_docx(filepath: str) -> str:
    if not _DOCX_AVAILABLE:
        return "[DOCX extraction unavailable — install python-docx: pip install python-docx]"

    try:
        doc = _DocxDocument(filepath)
        lines = [para.text for para in doc.paragraphs if para.text.strip()]
        # Also extract table cells
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        lines.append(cell.text.strip())
        return "\n".join(lines).strip() or "[No readable text found in this DOCX]"
    except Exception as exc:
        return f"[DOCX extraction error: {exc}]"


# ── Image OCR ─────────────────────────────────────────────────────────────────

def _from_image(filepath: str) -> str:
    if not _OCR_AVAILABLE:
        return "[Image OCR unavailable — install pytesseract and Pillow: pip install pytesseract Pillow]"

    _configure_tesseract()
    try:
        img = Image.open(filepath)
        # Convert to RGB in case of RGBA/palette images that Tesseract may not handle
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        text = pytesseract.image_to_string(img).strip()
        return text or "[No readable text detected in this image]"
    except pytesseract.TesseractNotFoundError:
        return (
            "[OCR engine not detected on system. Image stored safely.\n"
            "Download original file to inspect document, or install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki]"
        )
    except Exception as exc:
        return f"[Image OCR error: {exc}]"
