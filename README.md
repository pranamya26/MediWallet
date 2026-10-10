# MediWallet
MediVault — Your Medical History, All in One Place

A HealthTech solution for fragmented medical records and continuity of care.

1. Problem Statement

Lost in Transit: Fragmented Medical Records and Repeated Care Across Providers

Patients with long-term conditions often visit multiple doctors, clinics, diagnostic laboratories, and pharmacies. Their medical records are scattered across paper prescriptions, PDF reports, and photographs stored on their devices or shared through messaging applications.

When patients change doctors, move to another city, or visit an emergency department, their medical history may not be readily available. This can result in repeated diagnostic tests, incomplete medical information, delays in treatment, and potential medication-related problems.

MediVault addresses this problem by providing a centralized platform where patients can organize their medical records, review their health history, and securely share selected information with healthcare professionals.

2. Our Solution

MediVault is a web-based personal medical-record management application designed to help patients maintain and access their medical history in one place.

The application aims to make medical documents easier to organize, search, review, and share while giving patients control over access to their personal health information.

Key Objectives

- Bring scattered medical records together in one place.
- Maintain a chronological medical history.
- Make important health information easier to access.
- Help doctors review previous reports before deciding on further tests.
- Enable controlled sharing of medical records.
- Protect patient privacy and confidentiality.

3. Key Features

Patient Account and Medical Profile

- Patient registration, login, and logout.
- Store personal details such as name, date of birth, and emergency contact.
- Maintain blood group, allergies, existing conditions, and current medicines.
- Edit personal and medical information.

Medical Document Management

- Upload supported medical documents from a device.
- Support PDF files, JPG, JPEG, and PNG images.
- Support DOCX documents where implemented.
- Add document details, including date, category, hospital, and doctor.
- Preview, search, and organize medical documents.

Unified Medical History Timeline

- Display medical records in chronological order.
- Organize records into categories such as prescriptions, blood tests, scans, diagnoses, and discharge summaries.
- Search and filter records by date, name, and category.
- Open and review previous reports.

Emergency Health Summary

- Display important information such as allergies, current medicines, existing conditions, blood group, and emergency contact.
- Make important medical information easier to find during consultations.
- Clearly identify missing or unverified information.

Previous-Test Awareness

- Identify potentially similar earlier reports using available document metadata and text.
- Display the date and link to a previous report when a possible match is found.
- Help healthcare professionals review existing results before deciding whether another test is necessary.

The system provides a review aid only. It does not automatically decide whether a test should be performed.

Secure Medical Record Sharing

- Allow patients to select records for sharing.
- Support controlled access through a secure link or QR code where implemented.
- Provide expiry and revocation controls where implemented.
- Restrict access to authorized users and maintain access history where implemented.

Document Text Extraction

- Extract text from supported PDF files and document images.
- Use OCR to process scanned reports where configured.
- Allow extracted information to be reviewed before it is saved or used.

OCR output may contain errors and must not be treated as a confirmed medical diagnosis.

4. Technology Stack

Backend

- Python — application logic.
- Flask — web application framework.
- Flask-SQLAlchemy — database integration.
- Flask-Login — login session management.
- Werkzeug — web utilities and security-related functions.

Document Processing

- Pillow — image processing.
- pytesseract — Python integration for OCR.
- Tesseract OCR — OCR engine, installed separately.
- pdfplumber — PDF text extraction.
- PyMuPDF — PDF processing and page rendering.
- python-docx — DOCX document processing.

Other Libraries

- qrcode — QR code generation.
- pytest — automated testing.
- pytest-flask — Flask testing utilities.

The exact Python dependency versions and constraints are documented in "requirements.txt".

5. Project Structure

A suggested project structure is:

MediVault/
├── app.py
├── requirements.txt
├── README.md
├── models.py
├── routes.py
├── utils.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── profile.html
│   ├── records.html
│   └── share.html
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│   └── uploads/
└── tests/
    └── test_app.py

This is a suggested structure. Adapt the filenames and folders to match the actual files in the repository. Uploaded medical documents should be stored privately and should not be committed to GitHub.

6. Installation and Setup

Prerequisites

Install the following:

- Python 3.10 or a compatible Python version.
- pip.
- Git.
- Tesseract OCR if OCR functionality is used.

Step 1: Clone the repository

git clone <YOUR_GITHUB_REPOSITORY_URL>
cd MediVault

Replace the placeholder with your actual GitHub repository URL.

Step 2: Create a virtual environment

python -m venv .venv

Activate the environment.

Windows:

.venv\Scripts\activate

Linux or macOS:

source .venv/bin/activate

Step 3: Install dependencies

python -m pip install -r requirements.txt

Step 4: Install Tesseract OCR

Tesseract is a separate system dependency and is not installed by installing "pytesseract".

On Ubuntu or Debian-based Linux systems:

sudo apt update
sudo apt install tesseract-ocr

Verify the installation:

tesseract --version

On other operating systems, install the appropriate Tesseract package and configure its executable path if necessary.

Step 5: Configure environment variables

Create a local ".env" file if your application uses environment variables.

For example:

SECRET_KEY=replace_with_a_secure_random_value
DATABASE_URL=sqlite:///medivault.db

These are example settings. Your application must be configured to read the corresponding variables. Do not commit real secrets or credentials to GitHub.

Step 6: Initialize the database

Run the database initialization command or application setup procedure implemented in your project. For example, if your application creates its tables during initialization, follow the relevant instructions in "app.py".

Step 7: Run the application

python app.py

Open the local URL printed by Flask in your terminal, commonly:

http://127.0.0.1:5000

The exact command and URL depend on your application configuration.

7. Usage

1. Register a patient account and log in.
2. Enter personal and medical profile information.
3. Upload a medical document in a supported format.
4. Add its date, category, hospital, and doctor when available.
5. View uploaded records in the medical history timeline.
6. Search for earlier reports and review potential matches.
7. Open the emergency health summary.
8. Use the record-sharing feature if it has been implemented and configured.

8. Privacy and Security

Medical records contain sensitive personal information. MediVault is designed with the following security objectives:

- Authenticate users before granting access to private records.
- Enforce patient-specific authorization checks.
- Store uploaded files privately.
- Validate uploaded file types and enforce size limits.
- Use secure password handling and session configuration.
- Protect shared records using authorization, expiry, and revocation where implemented.
- Avoid exposing sensitive documents through unrestricted public URLs.
- Keep secrets and real patient data out of the source repository.

Security controls must be implemented and tested before the application is used with real medical records.

9. Open-Source Dependencies and Disclosure

MediVault uses third-party open-source Python packages and the Tesseract OCR engine. Their purposes, versions, and constraints are documented in "requirements.txt".

Third-party software and APIs are used to support web development, database access, document processing, OCR, QR code generation, and automated testing.

Any additional APIs, services, or libraries used in the final implementation should also be disclosed in this repository, along with their purpose and applicable licence information.

10. Testing

The project uses pytest and pytest-flask for automated testing.

Run the test suite with:

python -m pytest

Recommended test cases include:

- Patient registration and login.
- Unauthorized access to another patient's records.
- Uploading valid and invalid file types.
- Searching and filtering medical records.
- Handling missing document metadata.
- Processing text-based and scanned PDFs.
- Validating shared-link expiry and revocation.
- Handling OCR errors and unreadable documents.

Only tests that have actually been executed should be reported as passing.

11. Limitations and Future Enhancements

Potential future improvements include:

- Improved OCR accuracy and automatic metadata extraction.
- Support for additional document formats, including legacy DOC files.
- More advanced matching of previous tests and laboratory results.
- Improved doctor-facing record review.
- Integration with compatible healthcare information systems.
- Additional accessibility and multilingual support.
- Further security testing, backups, and production deployment improvements.

These enhancements depend on available development time, data quality, and integration requirements.

12. Disclaimer

MediVault is a medical-record organization and review-support prototype. It is not a substitute for professional medical advice, diagnosis, or treatment.

Automated text extraction, summaries, and possible duplicate-test warnings may be inaccurate. Healthcare professionals must independently review medical information and make clinical decisions.

The hackathon prototype should use simulated or appropriately authorized data. It should not be assumed to be ready for production healthcare use without further security, privacy, reliability, and compliance assessment.

13. Hackathon Information

Project: MediVault
Domain: HealthTech
Problem Statement: Lost in Transit: Fragmented Medical Records and Repeated Care Across Providers
Event: 24-Hour Web Development Hackathon — IIITDM Kancheepuram

Repository: Add your GitHub repository URL here.
Live Demo: Add your deployed application URL here.
Demo Video: Add your demonstration video URL here.

---

Built as a hackathon project to explore how patient-controlled digital medical records can support continuity of care.
