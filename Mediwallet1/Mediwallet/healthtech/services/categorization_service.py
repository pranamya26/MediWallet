"""
Automatic medical report categorization service.

Classifies medical documents into standard clinical health folders:
  • Diabetes / Sugar (diabetes_sugar)
  • Blood Pressure (blood_pressure)
  • Heart Health (heart_health)
  • Thyroid (thyroid)
  • Kidney (kidney)
  • Liver (liver)
  • General Health (general_health)
"""

from __future__ import annotations
import re
from typing import TypedDict


class CategoryInfo(TypedDict):
    key: str
    label: str
    description: str
    keywords: list[str]
    high_value_terms: list[str]


HEALTH_CATEGORIES: dict[str, CategoryInfo] = {
    "diabetes_sugar": {
        "key": "diabetes_sugar",
        "label": "Diabetes / Sugar",
        "description": "Blood sugar, glucose, HbA1c, insulin, and diabetic monitoring",
        "keywords": [
            "diabetes", "diabetic", "sugar", "glucose", "fbs", "ppbs", "rbs",
            "fasting blood sugar", "post prandial", "postprandial", "random blood sugar",
            "hba1c", "hba1-c", "glycated hemoglobin", "glycated haemoglobin", "hemoglobin a1c",
            "glycemic", "glycaemic", "insulin", "metformin", "glimepiride", "glipizide",
            "sitagliptin", "dapagliflozin", "empagliflozin", "vildagliptin", "gliclazide",
            "ketones", "ketoacidosis", "dka", "glucometer", "hypoglycemia", "hyperglycemia",
            "ogtt", "oral glucose tolerance", "c-peptide", "microvascular", "diabetic retinopathy",
            "diabetic nephropathy", "diabetic neuropathy", "januvia", "galvus", "glycomet",
            "trajenta", "forxiga", "jardiance", "rybelsus", "blood sugar"
        ],
        "high_value_terms": [
            "hba1c", "fasting blood sugar", "post prandial", "postprandial",
            "glycated hemoglobin", "fbs", "ppbs", "diabetes", "diabetic", "insulin", "metformin"
        ]
    },
    "blood_pressure": {
        "key": "blood_pressure",
        "label": "Blood Pressure",
        "description": "Hypertension, BP readings, and arterial pressure monitoring",
        "keywords": [
            "blood pressure", "bp", "hypertension", "hypertensive", "hypotension",
            "systolic", "diastolic", "sphygmomanometer", "mmhg", "high bp", "low bp",
            "amlodipine", "telmisartan", "losartan", "olmesartan", "valsartan", "ramipril",
            "enalapril", "lisinopril", "atenolol", "metoprolol", "bisoprolol", "carvedilol",
            "labetalol", "hydrochlorothiazide", "chlorthalidone", "indapamide", "nifedipine",
            "diltiazem", "clonidine", "cilnidipine", "essential hypertension", "preeclampsia",
            "arterial pressure", "ambulatory bp", "abpm", "norvasc", "telma", "cardace"
        ],
        "high_value_terms": [
            "blood pressure", "hypertension", "hypertensive", "systolic", "diastolic",
            "sphygmomanometer", "amlodipine", "telmisartan", "losartan", "ramipril"
        ]
    },
    "heart_health": {
        "key": "heart_health",
        "label": "Heart Health",
        "description": "ECG, Echo, cholesterol, lipid profile, and cardiology reports",
        "keywords": [
            "heart", "cardiac", "cardiology", "cardiologist", "ecg", "ekg", "echo",
            "echocardiogram", "echocardiography", "cholesterol", "lipid profile", "lipid panel",
            "triglycerides", "ldl", "hdl", "vldl", "total cholesterol", "troponin", "ck-mb",
            "bnp", "pro-bnp", "nt-probnp", "angina", "myocardial", "infarction", "coronary",
            "arrhythmia", "atrial fibrillation", "ischemic", "atherosclerosis", "stent",
            "angioplasty", "cabg", "bypass", "atorvastatin", "rosuvastatin", "simvastatin",
            "clopidogrel", "aspirin", "ecosprin", "ticagrelor", "heparin", "warfarin", "tmt",
            "treadmill test", "holter", "pacemaker", "ejection fraction", "lvef", "ventricle",
            "atrium", "myocardium", "pericardial", "valve", "aortic", "mitral", "cardiovascular",
            "coronary artery", "lipistat", "atorva", "rosuvas"
        ],
        "high_value_terms": [
            "lipid profile", "cholesterol", "echocardiogram", "ecg", "cardiac",
            "cardiologist", "troponin", "myocardial", "atorvastatin", "rosuvastatin", "ejection fraction"
        ]
    },
    "thyroid": {
        "key": "thyroid",
        "label": "Thyroid",
        "description": "TSH, T3, T4 hormone levels, thyroid function & endocrine health",
        "keywords": [
            "thyroid", "tsh", "thyroid stimulating hormone", "t3", "t4", "free t3",
            "ft3", "free t4", "ft4", "total t3", "total t4", "hypothyroid", "hypothyroidism",
            "hyperthyroid", "hyperthyroidism", "thyroxine", "levothyroxine", "eltroxin",
            "thyronorm", "euthyrox", "methimazole", "carbimazole", "propylthiouracil",
            "goiter", "goitre", "hashimoto", "graves", "anti-tpo", "thyroglobulin",
            "tsh receptor", "thyroiditis", "anti thyroglobulin", "ultrasound neck thyroid"
        ],
        "high_value_terms": [
            "thyroid", "tsh", "free t3", "free t4", "hypothyroidism", "hyperthyroidism",
            "levothyroxine", "thyroxine", "thyronorm", "eltroxin", "anti-tpo"
        ]
    },
    "kidney": {
        "key": "kidney",
        "label": "Kidney",
        "description": "Creatinine, urea, KFT/RFT, renal profile, and nephrology reports",
        "keywords": [
            "kidney", "renal", "nephrology", "nephrologist", "kft", "rft",
            "kidney function test", "renal function test", "creatinine", "serum creatinine",
            "urea", "blood urea", "bun", "blood urea nitrogen", "egfr", "glomerular filtration",
            "uric acid", "proteinuria", "microalbumin", "albumin creatinine ratio", "uacr",
            "urine routine", "urine analysis", "urinalysis", "dialysis", "hemodialysis",
            "nephritis", "glomerulonephritis", "ckd", "chronic kidney disease", "renal stone",
            "calculus", "nephrolithiasis", "hydronephrosis", "pyelonephritis", "creatinine clearance"
        ],
        "high_value_terms": [
            "kft", "rft", "creatinine", "serum creatinine", "renal function", "kidney function",
            "blood urea", "egfr", "nephrology", "dialysis", "microalbumin"
        ]
    },
    "liver": {
        "key": "liver",
        "label": "Liver",
        "description": "LFT, bilirubin, SGOT, SGPT, hepatitis & hepatobiliary testing",
        "keywords": [
            "liver", "hepatic", "hepatology", "hepatologist", "lft", "liver function test",
            "sgot", "sgpt", "ast", "alt", "aspartate aminotransferase", "alanine aminotransferase",
            "bilirubin", "total bilirubin", "direct bilirubin", "indirect bilirubin",
            "alkaline phosphatase", "alp", "gamma-gt", "ggt", "ggtp", "serum albumin",
            "serum globulin", "a/g ratio", "hepatitis", "hepatitis b", "hepatitis c", "hbsag",
            "hcv", "cirrhosis", "fatty liver", "nafld", "nash", "fibroscan", "jaundice",
            "ascites", "portal hypertension", "cholecystitis", "gallbladder", "udiliv", "ursodiol"
        ],
        "high_value_terms": [
            "lft", "liver function test", "liver function", "bilirubin", "sgpt", "sgot",
            "hepatic", "hepatitis", "fatty liver", "cirrhosis", "fibroscan"
        ]
    },
    "general_health": {
        "key": "general_health",
        "label": "General Health",
        "description": "Complete blood counts (CBC), vitamins, checkups & general consultations",
        "keywords": [
            "general health", "general checkup", "wellness", "master health", "physical exam",
            "consultation", "cbc", "complete blood count", "hemogram", "complete hemogram",
            "hemoglobin", "haemoglobin", "wbc", "rbc", "platelet", "platelet count", "pcv",
            "mcv", "mch", "mchc", "esr", "crp", "c-reactive protein", "vitamin d", "vitamin b12",
            "calcium", "electrolytes", "sodium", "potassium", "chloride", "prescription",
            "discharge summary", "clinic", "hospital", "routine"
        ],
        "high_value_terms": [
            "cbc", "complete blood count", "hemogram", "complete hemogram", "general checkup",
            "master health", "vitamin d", "vitamin b12"
        ]
    }
}

VALID_HEALTH_CATEGORIES = set(HEALTH_CATEGORIES.keys())


def categorize_record(
    text: str = "",
    filename: str = "",
    notes: str = "",
    doc_type: str = "",
    hospital: str = "",
    doctor: str = ""
) -> dict:
    """
    Analyze document text and metadata to classify into a health category folder.

    Returns dict:
      {
        "category": "diabetes_sugar",
        "label": "Diabetes / Sugar",
        "confidence": 0.85,
        "matched_terms": ["glucose", "hba1c"]
      }
    """
    # Combine texts with different weighting
    text_corpus = (text or "").lower()
    filename_corpus = (filename or "").lower()
    notes_corpus = (notes or "").lower()
    doctor_hospital = f"{doctor or ''} {hospital or ''}".lower()

    scores: dict[str, float] = {k: 0.0 for k in HEALTH_CATEGORIES}
    matches: dict[str, list[str]] = {k: [] for k in HEALTH_CATEGORIES}

    for cat_key, info in HEALTH_CATEGORIES.items():
        high_values = set(info.get("high_value_terms", []))

        for kw in info["keywords"]:
            kw_clean = kw.lower()
            pattern = r'\b' + re.escape(kw_clean) + r'\b'
            
            # Check in extracted text
            count = len(re.findall(pattern, text_corpus))
            if count > 0:
                base_weight = 3.5 if kw_clean in high_values else 1.2
                # Diminishing returns for multiple occurrences
                score_gain = base_weight * (1.0 + min(count - 1, 4) * 0.4)
                scores[cat_key] += score_gain
                matches[cat_key].append(kw_clean)

            # Check in filename (strong signal)
            if re.search(pattern, filename_corpus):
                fn_weight = 4.0 if kw_clean in high_values else 2.5
                scores[cat_key] += fn_weight
                if kw_clean not in matches[cat_key]:
                    matches[cat_key].append(f"filename:{kw_clean}")

            # Check in patient notes
            if re.search(pattern, notes_corpus):
                notes_weight = 3.0 if kw_clean in high_values else 1.5
                scores[cat_key] += notes_weight
                if kw_clean not in matches[cat_key]:
                    matches[cat_key].append(f"notes:{kw_clean}")

            # Check in doctor/hospital specialty
            if re.search(pattern, doctor_hospital):
                scores[cat_key] += 2.0
                if kw_clean not in matches[cat_key]:
                    matches[cat_key].append(f"clinic:{kw_clean}")

    # Prioritize specific organ/condition categories over general_health
    # If a specific category scored > 1.5, we prefer it over general_health unless general_health is 2.5x higher
    best_cat = "general_health"
    max_score = 0.0

    # First evaluate specific categories (excluding general_health)
    specific_cats = [k for k in HEALTH_CATEGORIES if k != "general_health"]
    best_specific = None
    best_specific_score = 0.0

    for cat in specific_cats:
        if scores[cat] > best_specific_score:
            best_specific_score = scores[cat]
            best_specific = cat

    if best_specific and best_specific_score >= 1.2:
        best_cat = best_specific
        max_score = best_specific_score
    elif scores["general_health"] > 0:
        best_cat = "general_health"
        max_score = scores["general_health"]
    else:
        best_cat = "general_health"
        max_score = 0.0

    category_info = HEALTH_CATEGORIES[best_cat]
    confidence = min(round((max_score / 10.0), 2), 0.99) if max_score > 0 else 0.50

    return {
        "category": best_cat,
        "label": category_info["label"],
        "confidence": confidence,
        "matched_terms": matches[best_cat][:6],
        "all_scores": {k: round(v, 2) for k, v in scores.items() if v > 0}
    }


def get_category_metadata(category_key: str) -> dict:
    """Return presentation details for a health category."""
    cat = HEALTH_CATEGORIES.get(category_key, HEALTH_CATEGORIES["general_health"])
    return {
        "key": cat["key"],
        "label": cat["label"],
        "description": cat["description"]
    }


def get_all_categories_summary() -> list[dict]:
    """Return all categories with metadata."""
    return [
        {
            "key": info["key"],
            "label": info["label"],
            "description": info["description"]
        }
        for info in HEALTH_CATEGORIES.values()
    ]
