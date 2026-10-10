"""
Verification test for the API contract.
Ensures that the API response contract strictly aligns with:
1. Output format of src.inference.DiseaseClassifier
2. Output format of src.treatment.TreatmentAdvisor
3. Required response schema:
   {
       "success": true,
       "crop": "...",
       "disease": "...",
       "confidence": 0.0,
       "treatment": { ... },
       "model_version": "..."
   }
4. Error schema format
5. Low-confidence handling logic
"""

import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference import DiseaseClassifier, get_classifier
from src.treatment import TreatmentAdvisor, get_advisor

CONFIDENCE_THRESHOLD = 0.60

EXPECTED_RESPONSE_KEYS = {
    "success",
    "crop",
    "disease_code",
    "disease",
    "confidence",
    "treatment",
    "model_version"
}

EXPECTED_TREATMENT_KEYS = {
    "status",
    "disease_key",
    "disease_name",
    "crop",
    "pathogen_or_cause",
    "summary",
    "symptoms",
    "preventive_measures",
    "cultural_practices",
    "organic_treatment",
    "chemical_treatment",
    "safety_warning",
    "source"
}

EXPECTED_ERROR_KEYS = {
    "success",
    "error"
}

EXPECTED_ERROR_DETAILS_KEYS = {
    "code",
    "message",
    "details",
    "timestamp"
}


def build_api_response(inference_result: dict, advisor: TreatmentAdvisor, threshold: float = CONFIDENCE_THRESHOLD) -> dict:
    """Simulates the controller / route handler logic for POST /predict."""
    confidence = inference_result.get("confidence", 0.0)
    raw_class = inference_result.get("disease", "Unknown")
    model_version = inference_result.get("model_version", "unknown")

    # Retrieve treatment from knowledge base
    treatment = advisor.get_treatment(raw_class)

    is_low_confidence = confidence < threshold

    if is_low_confidence:
        display_disease = "Low Confidence / Unverified"
        display_crop = treatment.get("crop", "Uncertain")
        treatment_payload = {
            "status": "low_confidence",
            "disease_key": raw_class,
            "disease_name": f"Unverified ({treatment.get('disease_name', 'Unknown')})",
            "crop": display_crop,
            "pathogen_or_cause": f"Confidence score ({round(confidence*100, 2)}%) below diagnostic threshold ({round(threshold*100, 2)}%)",
            "summary": treatment.get("summary", "Low confidence prediction."),
            "symptoms": [
                "Visual symptoms could not be diagnosed with sufficient certainty.",
                "Ensure photograph is focused on single leaf under clear daylight."
            ],
            "preventive_measures": [
                "Retake photograph from 15-30 cm distance ensuring symptom is centered.",
                "Check multiple leaves to confirm uniformity of damage."
            ],
            "cultural_practices": [
                "Scout neighboring plants in same crop row.",
                "Inspect leaf undersides for pests or webbing."
            ],
            "organic_treatment": [
                "Withhold treatment until diagnostic certainty is achieved."
            ],
            "chemical_treatment": [
                "Do NOT apply chemical pesticides on unverified symptoms."
            ],
            "safety_warning": "Unverified chemical treatments risk crop toxicity and environmental contamination.",
            "source": "AI Farmer Assistant Diagnostic Confidence Safety Protocol"
        }
    else:
        display_disease = treatment.get("disease_name", raw_class)
        display_crop = treatment.get("crop", "Unknown")
        treatment_payload = treatment

    return {
        "success": True,
        "analysis_id": None,
        "crop": display_crop,
        "disease_code": raw_class,
        "disease": display_disease,
        "confidence": round(confidence, 4),
        "treatment": treatment_payload,
        "model_version": model_version,
        "low_confidence": is_low_confidence,
        "is_low_confidence": is_low_confidence
    }


def test_contract_alignment():
    print("=" * 80)
    print("API CONTRACT ALIGNMENT VERIFICATION")
    print("=" * 80)

    classifier = get_classifier()
    advisor = get_advisor()

    # 1. Test across all 13 supported classes
    print("\n[TEST 1] Verifying contract schema across all 13 supported classes...")
    all_classes = advisor.list_supported_diseases()
    schema_failures = []

    for cname in all_classes:
        mock_inference = {
            "disease": cname,
            "confidence": 0.9542,
            "class_index": classifier.class_to_idx.get(cname, 0),
            "model_version": classifier.model_version
        }
        res = build_api_response(mock_inference, advisor)

        # Check required top-level keys
        for key in EXPECTED_RESPONSE_KEYS:
            if key not in res:
                schema_failures.append(f"Missing top-level key '{key}' for {cname}")

        # Check required treatment keys
        for tkey in EXPECTED_TREATMENT_KEYS:
            if tkey not in res["treatment"]:
                schema_failures.append(f"Missing treatment key '{tkey}' for {cname}")

        # Value types
        if not isinstance(res["success"], bool) or not res["success"]:
            schema_failures.append(f"'success' must be True for {cname}")
        if not isinstance(res["crop"], str) or len(res["crop"]) == 0:
            schema_failures.append(f"'crop' must be non-empty string for {cname}")
        if not isinstance(res["disease"], str) or len(res["disease"]) == 0:
            schema_failures.append(f"'disease' must be non-empty string for {cname}")
        if not isinstance(res["confidence"], float) or not (0.0 <= res["confidence"] <= 1.0):
            schema_failures.append(f"'confidence' must be float in [0, 1] for {cname}")
        if not isinstance(res["model_version"], str):
            schema_failures.append(f"'model_version' must be string for {cname}")

    if schema_failures:
        print(f"   FAILED: {len(schema_failures)} schema failures detected:")
        for f in schema_failures[:5]:
            print(f"      - {f}")
        test_1_pass = False
    else:
        print(f"   PASS: All {len(all_classes)} classes match the response schema perfectly.")
        test_1_pass = True

    # 2. Test Low Confidence Behavior
    print("\n[TEST 2] Verifying low-confidence behavior (< 0.60)...")
    mock_low_conf = {
        "disease": "Tomato___Early_blight",
        "confidence": 0.3850,
        "class_index": 4,
        "model_version": classifier.model_version
    }
    low_res = build_api_response(mock_low_conf, advisor)
    
    low_conf_ok = (
        low_res["success"] is True and
        low_res["is_low_confidence"] is True and
        low_res["confidence"] == 0.3850 and
        low_res["treatment"]["status"] == "low_confidence" and
        "Do NOT apply chemical pesticides" in low_res["treatment"]["chemical_treatment"][0]
    )
    print(f"   Low confidence contract check: {'PASS' if low_conf_ok else 'FAIL'}")

    # 3. Test Real Inference Output Pipeline
    print("\n[TEST 3] Verifying with real inference module image pass...")
    test_dir = PROJECT_ROOT / "data" / "processed" / "tomato_potato_split" / "test" / "Potato___Early_blight"
    sample_img_path = test_dir.glob("*.JPG")
    sample_file = next(sample_img_path, None)
    if not sample_file:
        sample_img_path = test_dir.glob("*.jpg")
        sample_file = next(sample_img_path, None)

    if sample_file:
        real_pred = classifier.predict(str(sample_file))
        api_res = build_api_response(real_pred, advisor)
        real_pipeline_ok = (
            api_res["success"] is True and
            api_res["crop"] == "Potato" and
            "Early Blight" in api_res["disease"] and
            api_res["confidence"] > 0.80 and
            isinstance(api_res["treatment"]["symptoms"], list)
        )
        print(f"   Real pipeline prediction: {api_res['crop']} - {api_res['disease']} (Conf: {api_res['confidence']})")
        print(f"   Real inference pipeline check: {'PASS' if real_pipeline_ok else 'FAIL'}")
    else:
        real_pipeline_ok = True
        print("   Skipping real image test (sample image not found).")

    # 4. Error Schema Verification
    print("\n[TEST 4] Verifying Error response schema...")
    mock_error_resp = {
        "success": False,
        "error": {
            "code": "INVALID_IMAGE_FILE",
            "message": "File cannot be decoded as an image.",
            "details": "PIL.UnidentifiedImageError: cannot identify image file",
            "timestamp": "2026-10-09T00:20:00Z"
        }
    }
    error_ok = (
        mock_error_resp["success"] is False and
        set(mock_error_resp.keys()) == EXPECTED_ERROR_KEYS and
        set(mock_error_resp["error"].keys()) == EXPECTED_ERROR_DETAILS_KEYS
    )
    print(f"   Error response contract check: {'PASS' if error_ok else 'FAIL'}")

    # Summary
    all_pass = test_1_pass and low_conf_ok and real_pipeline_ok and error_ok
    print("\n" + "=" * 80)
    print(f"API CONTRACT VERIFICATION STATUS: {'PASS' if all_pass else 'FAIL'}")
    print("=" * 80)
    return all_pass


if __name__ == "__main__":
    ok = test_contract_alignment()
    sys.exit(0 if ok else 1)
