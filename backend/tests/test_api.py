"""
Automated API Test Suite for AI Farmer Assistant FastAPI Backend.

Tests:
1. GET /health (Standard diagnostics and status)
2. Valid image POST /predict with frontend field 'image' and compatibility field 'file'
3. Missing image parameter & empty request body (HTTP 400)
4. Empty file upload (0 bytes) (HTTP 400)
5. Corrupted image bytes (HTTP 422)
6. Unsupported file format (.txt, .pdf, and disguised BMP named .jpg) (HTTP 415)
7. Oversized file upload (> 10 MB limit) (HTTP 413)
8. Response schema & low-confidence diagnostic behavior
9. Model unavailable behavior (health degradation and HTTP 503)
10. Correct disease-code mapping & treatment integration
11. CORS headers configuration for React frontend development origin
12. Real model inference smoke test
"""

import sys
import io
import json
import uuid
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api import app
from src.schemas import HealthResponse, PredictionResponse, ErrorResponse
from src.inference import get_classifier, set_classifier
from src.treatment import get_advisor


def run_api_tests():
    print("=" * 80)
    print("FASTAPI BACKEND AUTOMATED TEST SUITE")
    print("=" * 80)

    client = TestClient(app)
    results = {}

    # -------------------------------------------------------------
    # 1. GET /health
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing GET /health...")
    resp_health = client.get("/health")
    print(f"   Status: {resp_health.status_code}")
    print(f"   Body: {resp_health.json()}")

    try:
        health_data = HealthResponse.model_validate(resp_health.json())
        test_1_ok = (
            resp_health.status_code == 200 and
            health_data.status == "healthy" and
            health_data.model_loaded is True and
            health_data.supported_classes == 13 and
            health_data.model_version is not None and
            len(health_data.model_version) > 0
        )
    except Exception as e:
        print(f"   Validation Error: {e}")
        test_1_ok = False

    print(f"   GET /health Test: {'PASS' if test_1_ok else 'FAIL'}")
    results["health"] = test_1_ok

    # -------------------------------------------------------------
    # 1b. Verify POST /predict requires authentication
    # -------------------------------------------------------------
    print("\n[TEST 1b] Testing Unauthenticated POST /predict rejection...")
    resp_unauth = client.post("/predict")
    unauth_ok = (
        resp_unauth.status_code == 401 and
        resp_unauth.json().get("error", {}).get("code") == "UNAUTHORIZED"
    )
    print(f"   Unauthenticated /predict Status: {resp_unauth.status_code}, Code: {resp_unauth.json().get('error', {}).get('code')}")
    print(f"   Unauthenticated Rejection Test: {'PASS' if unauth_ok else 'FAIL'}")
    results["unauth_protection"] = unauth_ok

    # Authenticate client for protected endpoint tests
    print("\n[AUTH SETUP] Authenticating test user for protected endpoint testing...")
    test_email = f"apitester_{uuid.uuid4().hex[:8]}@farm.org"
    test_pwd = "CorrectHorseBattery99!"
    reg_resp = client.post("/auth/register", json={
        "full_name": "API Tester",
        "email": test_email,
        "password": test_pwd
    })
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"

    login_resp = client.post("/auth/login", json={
        "email": test_email,
        "password": test_pwd
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    csrf_token = login_resp.cookies.get("csrf_token")
    assert csrf_token is not None, "CSRF cookie missing on login"
    client.headers.update({"X-CSRF-Token": csrf_token})
    print(f"   Authenticated as {test_email} with CSRF token attached.")

    # Prepare sample valid image
    test_img_dir = PROJECT_ROOT / "data" / "processed" / "tomato_potato_split" / "test" / "Potato___Early_blight"
    sample_img = next(test_img_dir.glob("*.JPG"), None) if test_img_dir.exists() else None
    if not sample_img and test_img_dir.exists():
        sample_img = next(test_img_dir.glob("*.jpg"), None)

    if sample_img:
        with open(sample_img, "rb") as f:
            valid_image_bytes = f.read()
    else:
        buf = io.BytesIO()
        Image.new("RGB", (224, 224), color=(34, 139, 34)).save(buf, format="JPEG")
        valid_image_bytes = buf.getvalue()

    # -------------------------------------------------------------
    # 2. Valid Image POST /predict (Frontend field 'image' & field 'file')
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing Valid Image POST /predict...")
    # 2a. Field name 'image' (as sent by React frontend analysisService.js)
    resp_image_field = client.post(
        "/predict",
        files={"image": ("leaf.jpg", valid_image_bytes, "image/jpeg")}
    )
    print(f"   2a. Field 'image' Status: {resp_image_field.status_code}")
    image_field_json = resp_image_field.json()
    print(f"       Crop: {image_field_json.get('crop')}, Disease Code: {image_field_json.get('disease_code')}")
    print(f"       Disease: {image_field_json.get('disease')}, Conf: {image_field_json.get('confidence')}")
    print(f"       Summary: {image_field_json.get('treatment', {}).get('summary')}")

    try:
        pred_data_image = PredictionResponse.model_validate(image_field_json)
        test_2a_ok = (
            resp_image_field.status_code == 200 and
            pred_data_image.success is True and
            pred_data_image.disease_code is not None and
            len(pred_data_image.disease_code) > 0 and
            pred_data_image.crop in ["Potato", "Tomato"] and
            pred_data_image.confidence > 0.0 and
            len(pred_data_image.treatment.summary) > 0 and
            len(pred_data_image.treatment.symptoms) > 0 and
            len(pred_data_image.treatment.preventive_measures) > 0 and
            len(pred_data_image.treatment.chemical_treatment) > 0
        )
    except Exception as e:
        print(f"   Validation Error (2a): {e}")
        test_2a_ok = False

    # 2b. Field name 'file' (backward compatible)
    resp_file_field = client.post(
        "/predict",
        files={"file": ("leaf.jpg", valid_image_bytes, "image/jpeg")}
    )
    test_2b_ok = resp_file_field.status_code == 200 and resp_file_field.json().get("success") is True

    test_2_ok = test_2a_ok and test_2b_ok
    print(f"   Valid Image /predict Test: {'PASS' if test_2_ok else 'FAIL'}")
    results["valid_image"] = test_2_ok

    # -------------------------------------------------------------
    # 3. Missing Image & Empty Request Body (HTTP 400)
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing Missing Image & Empty Body handling...")
    # 3a. Form without image/file field
    resp_missing = client.post("/predict", data={"other_field": "no_image"})
    missing_ok = (
        resp_missing.status_code == 400 and
        resp_missing.json().get("success") is False and
        resp_missing.json().get("error", {}).get("code") == "MISSING_FILE" and
        (resp_missing.json().get("message") is not None or resp_missing.json().get("detail") is not None)
    )

    # 3b. Completely empty POST body
    resp_empty_body = client.post("/predict")
    empty_body_ok = resp_empty_body.status_code == 400 and resp_empty_body.json().get("success") is False

    test_3_ok = missing_ok and empty_body_ok
    print(f"   Missing Image Test: {'PASS' if test_3_ok else 'FAIL'}")
    results["missing_image"] = test_3_ok

    # -------------------------------------------------------------
    # 4. Empty File Upload (0 bytes) (HTTP 400)
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing Empty File Upload (0 bytes)...")
    resp_empty_file = client.post(
        "/predict",
        files={"image": ("empty.jpg", b"", "image/jpeg")}
    )
    empty_file_ok = (
        resp_empty_file.status_code == 400 and
        resp_empty_file.json().get("success") is False and
        resp_empty_file.json().get("error", {}).get("code") == "EMPTY_FILE" and
        (resp_empty_file.json().get("message") is not None or resp_empty_file.json().get("detail") is not None)
    )
    print(f"   Empty File Test: {'PASS' if empty_file_ok else 'FAIL'}")
    results["empty_file"] = empty_file_ok

    # -------------------------------------------------------------
    # 5. Invalid / Corrupted Image Bytes (HTTP 422)
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing Corrupted Image Bytes...")
    resp_corrupt = client.post(
        "/predict",
        files={"image": ("corrupted.jpg", b"NOT_A_VALID_IMAGE_RANDOM_GARBAGE_BYTES", "image/jpeg")}
    )
    corrupt_ok = (
        resp_corrupt.status_code == 422 and
        resp_corrupt.json().get("success") is False and
        resp_corrupt.json().get("error", {}).get("code") == "CORRUPTED_IMAGE"
    )
    print(f"   Corrupted Image Test: {'PASS' if corrupt_ok else 'FAIL'}")
    results["corrupted_image"] = corrupt_ok

    # -------------------------------------------------------------
    # 6. Unsupported File Formats (HTTP 415)
    # -------------------------------------------------------------
    print("\n[TEST 6] Testing Unsupported File Formats (.txt, .pdf, disguised format)...")
    # 6a. Text file
    resp_txt = client.post(
        "/predict",
        files={"image": ("symptoms.txt", b"Blight symptoms observed", "text/plain")}
    )
    txt_ok = (
        resp_txt.status_code == 415 and
        resp_txt.json().get("error", {}).get("code") == "UNSUPPORTED_MEDIA_TYPE"
    )

    # 6b. PDF file
    resp_pdf = client.post(
        "/predict",
        files={"image": ("report.pdf", b"%PDF-1.4...", "application/pdf")}
    )
    pdf_ok = (
        resp_pdf.status_code == 415 and
        resp_pdf.json().get("error", {}).get("code") == "UNSUPPORTED_MEDIA_TYPE"
    )

    # 6c. Disguised BMP file named .jpg (content validation, not just extension)
    bmp_buf = io.BytesIO()
    Image.new("RGB", (64, 64), color="blue").save(bmp_buf, format="BMP")
    resp_bmp = client.post(
        "/predict",
        files={"image": ("disguised.jpg", bmp_buf.getvalue(), "image/jpeg")}
    )
    bmp_ok = (
        resp_bmp.status_code == 415 and
        resp_bmp.json().get("error", {}).get("code") == "UNSUPPORTED_MEDIA_TYPE"
    )

    test_6_ok = txt_ok and pdf_ok and bmp_ok
    print(f"   Unsupported File Test: {'PASS' if test_6_ok else 'FAIL'}")
    results["unsupported_file"] = test_6_ok

    # -------------------------------------------------------------
    # 7. Oversized Upload (> 10 MB Limit) (HTTP 413)
    # -------------------------------------------------------------
    print("\n[TEST 7] Testing Oversized Upload (> 10 MB limit)...")
    oversized_bytes = b"0" * (10 * 1024 * 1024 + 512)
    resp_oversized = client.post(
        "/predict",
        files={"image": ("huge.jpg", oversized_bytes, "image/jpeg")}
    )
    oversized_ok = (
        resp_oversized.status_code == 413 and
        resp_oversized.json().get("success") is False and
        resp_oversized.json().get("error", {}).get("code") == "FILE_TOO_LARGE"
    )
    print(f"   Oversized Upload Test: {'PASS' if oversized_ok else 'FAIL'}")
    results["oversized_upload"] = oversized_ok

    # -------------------------------------------------------------
    # 8. Response Schema & Low-Confidence Diagnostic Behavior
    # -------------------------------------------------------------
    print("\n[TEST 8] Testing Schema & Low-Confidence Behavior...")
    resp_low_conf = client.post(
        "/predict?confidence_threshold=0.9999",
        files={"image": ("leaf.jpg", valid_image_bytes, "image/jpeg")}
    )
    low_json = resp_low_conf.json()
    try:
        low_model = PredictionResponse.model_validate(low_json)
        low_ok = (
            resp_low_conf.status_code == 200 and
            low_model.success is True and
            low_model.low_confidence is True and
            low_model.is_low_confidence is True and
            "Low Confidence" in low_model.disease and
            low_model.disease_code is not None and
            low_model.treatment.status == "low_confidence" and
            len(low_model.treatment.summary) > 0
        )
    except Exception as e:
        print(f"   Validation Error (8): {e}")
        low_ok = False

    print(f"   Low Confidence Test: {'PASS' if low_ok else 'FAIL'}")
    results["low_confidence"] = low_ok

    # -------------------------------------------------------------
    # 9. Model Unavailable Handling
    # -------------------------------------------------------------
    print("\n[TEST 9] Testing Model Unavailable Handling...")
    saved_classifier = get_classifier()
    try:
        # Simulate model being unavailable
        set_classifier(None)
        
        # Health check should report degraded
        resp_degraded_health = client.get("/health")
        degraded_health_ok = (
            resp_degraded_health.status_code == 200 and
            resp_degraded_health.json().get("status") == "degraded" and
            resp_degraded_health.json().get("model_loaded") is False
        )
        print(f"   9a. Degraded Health Status: {resp_degraded_health.status_code}, Body: {resp_degraded_health.json()}")

        # Predict should reject with HTTP 503
        resp_503 = client.post(
            "/predict",
            files={"image": ("leaf.jpg", valid_image_bytes, "image/jpeg")}
        )
        predict_503_ok = (
            resp_503.status_code == 503 and
            resp_503.json().get("error", {}).get("code") == "MODEL_NOT_READY"
        )
        print(f"   9b. Predict when Model Unavailable: Status {resp_503.status_code}, Code: {resp_503.json().get('error', {}).get('code')}")

        model_unavailable_ok = degraded_health_ok and predict_503_ok
    finally:
        # Restore normal classifier
        set_classifier(saved_classifier)

    # Verify restored state
    restored_health = client.get("/health")
    restore_ok = restored_health.status_code == 200 and restored_health.json().get("model_loaded") is True

    test_9_ok = model_unavailable_ok and restore_ok
    print(f"   Model Unavailable Test: {'PASS' if test_9_ok else 'FAIL'}")
    results["model_unavailable"] = test_9_ok

    # -------------------------------------------------------------
    # 10. Disease Code Mapping & Treatment Response Structure
    # -------------------------------------------------------------
    print("\n[TEST 10] Testing Disease-Code Mapping & Treatment Structure...")
    advisor = get_advisor()
    supported_classes = advisor.list_supported_diseases()
    treatment_structure_ok = len(supported_classes) == 13
    for dcode in supported_classes:
        t = advisor.get_treatment(dcode)
        if (
            not t.get("disease_key") or
            not t.get("disease_name") or
            not t.get("crop") or
            not t.get("summary") or
            not t.get("preventive_measures") or
            not t.get("chemical_treatment") or
            not t.get("safety_warning")
        ):
            treatment_structure_ok = False
            break

    print(f"   Treatment Structure Test: {'PASS' if treatment_structure_ok else 'FAIL'}")
    results["treatment_structure"] = treatment_structure_ok

    # -------------------------------------------------------------
    # 11. CORS Configuration for React Frontend (http://localhost:5173)
    # -------------------------------------------------------------
    print("\n[TEST 11] Testing CORS Configuration for React Frontend Origin...")
    cors_resp = client.options(
        "/predict",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
    )
    allowed_origin = cors_resp.headers.get("access-control-allow-origin")
    allow_credentials = cors_resp.headers.get("access-control-allow-credentials")
    cors_ok = (
        cors_resp.status_code == 200 and
        allowed_origin == "http://localhost:5173" and
        allow_credentials == "true"
    )
    print(f"   CORS Status: {cors_resp.status_code}")
    print(f"   Allowed Origin: {allowed_origin}, Allow Credentials: {allow_credentials}")
    print(f"   CORS Test: {'PASS' if cors_ok else 'FAIL'}")
    results["cors"] = cors_ok

    # -------------------------------------------------------------
    # 12. Real Model Inference Smoke Test
    # -------------------------------------------------------------
    print("\n[TEST 12] Performing Real Model Inference Smoke Test...")
    smoke_resp = client.post(
        "/predict",
        files={"image": ("test_leaf.jpg", valid_image_bytes, "image/jpeg")}
    )
    smoke_data = smoke_resp.json()
    smoke_ok = (
        smoke_resp.status_code == 200 and
        smoke_data.get("success") is True and
        smoke_data.get("disease_code") in supported_classes and
        0.0 <= smoke_data.get("confidence", -1) <= 1.0 and
        smoke_data.get("analysis_id") is not None and
        len(smoke_data.get("analysis_id", "")) > 0
    )
    print(f"   Smoke Test Prediction:")
    print(f"     Crop: {smoke_data.get('crop')}")
    print(f"     Disease Code: {smoke_data.get('disease_code')}")
    print(f"     Disease: {smoke_data.get('disease')}")
    print(f"     Confidence: {smoke_data.get('confidence')}")
    print(f"     Model Version: {smoke_data.get('model_version')}")
    print(f"     Summary: {smoke_data.get('treatment', {}).get('summary')}")
    print(f"   Real Model Smoke Test: {'PASS' if smoke_ok else 'FAIL'}")
    results["real_model_smoke_test"] = smoke_ok

    # -------------------------------------------------------------
    # Final Summary
    # -------------------------------------------------------------
    all_passed = all(results.values())
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print("\n" + "=" * 80)
    print(f"FASTAPI SUITE STATUS: {'PASS' if all_passed else 'FAIL'}")
    print("=" * 80)
    for k, v in results.items():
        print(f"  {k.upper()}: {'PASS' if v else 'FAIL'}")
    print(f"\nTOTAL TESTS PASSED: {passed_count}/{total_count}")

    return all_passed, results


if __name__ == "__main__":
    passed, _ = run_api_tests()
    sys.exit(0 if passed else 1)
