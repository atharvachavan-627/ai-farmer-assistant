"""
Comprehensive frontend API integration test script.
Tests all scenarios from the user requirements against the live backend.
"""
import requests
import os
import sys
import io
import json
import tempfile

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://127.0.0.1:8000"
DATA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "plantvillage", "plantvillage dataset", "color")

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = {}

def get_first_image(folder_name):
    """Get first image from a dataset folder."""
    folder_path = os.path.join(DATA_ROOT, folder_name)
    if not os.path.exists(folder_path):
        return None
    for f in sorted(os.listdir(folder_path)):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            return os.path.join(folder_path, f)
    return None

def test_health():
    """Test 0: Health endpoint."""
    print("\n" + "=" * 60)
    print("TEST 0: Health Check (/health)")
    print("=" * 60)
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        data = resp.json()
        ok = resp.status_code == 200 and data.get("status") == "healthy" and data.get("model_loaded") is True
        print(f"  Status: {resp.status_code}")
        print(f"  Model: {data.get('model_version')}")
        print(f"  Device: {data.get('device')}")
        print(f"  Classes: {data.get('supported_classes')}")
        results["HEALTH_CHECK"] = PASS if ok else FAIL
        print(f"  Result: {results['HEALTH_CHECK']}")
        return ok
    except Exception as e:
        print(f"  Error: {e}")
        results["HEALTH_CHECK"] = FAIL
        return False

def test_frontend_html():
    """Test 1: Frontend HTML is served."""
    print("\n" + "=" * 60)
    print("TEST 1: Frontend HTML Served (/)")
    print("=" * 60)
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=10)
        html = resp.text
        checks = {
            "Status 200": resp.status_code == 200,
            "Has <title>": "AI Farmer Assistant" in html,
            "Has hero section": 'id="heroSection"' in html,
            "Has upload section": 'id="uploadSection"' in html,
            "Has loading section": 'id="loadingSection"' in html,
            "Has results section": 'id="resultsSection"' in html,
            "Has error section": 'id="errorSection"' in html,
            "Has file input": 'id="fileInput"' in html,
            "Has analyze button": 'id="analyzeBtn"' in html,
            "Has try again button": 'id="tryAgainBtn"' in html,
            "Has confidence bar": 'id="confidenceBar"' in html,
            "Has tabs": 'role="tablist"' in html,
            "Has app.js": '/static/app.js' in html,
            "Has styles.css": '/static/styles.css' in html,
        }
        all_ok = all(checks.values())
        for name, ok in checks.items():
            print(f"  {PASS if ok else FAIL} {name}")
        results["FRONTEND_HTML"] = PASS if all_ok else FAIL
        return all_ok
    except Exception as e:
        print(f"  Error: {e}")
        results["FRONTEND_HTML"] = FAIL
        return False

def test_static_css():
    """Test 2: CSS is served correctly."""
    print("\n" + "=" * 60)
    print("TEST 2: Static CSS (/static/styles.css)")
    print("=" * 60)
    try:
        resp = requests.get(f"{BASE_URL}/static/styles.css", timeout=10)
        ok = resp.status_code == 200 and "text/css" in resp.headers.get("Content-Type", "")
        content = resp.text
        css_checks = {
            "Has CSS variables": "--color-primary" in content,
            "Has responsive breakpoints": "@media" in content,
            "Has hero styles": ".hero" in content,
            "Has drop-zone": ".drop-zone" in content,
            "Has confidence bar": ".confidence-bar" in content,
            "Has animations": "@keyframes" in content,
            "Has button styles": ".btn-primary" in content,
        }
        all_ok = ok and all(css_checks.values())
        print(f"  {PASS if ok else FAIL} Status 200 with text/css")
        print(f"  Content-Length: {len(content)} bytes")
        for name, c in css_checks.items():
            print(f"  {PASS if c else FAIL} {name}")
        results["STATIC_CSS"] = PASS if all_ok else FAIL
        return all_ok
    except Exception as e:
        print(f"  Error: {e}")
        results["STATIC_CSS"] = FAIL
        return False

def test_static_js():
    """Test 3: JS is served correctly."""
    print("\n" + "=" * 60)
    print("TEST 3: Static JS (/static/app.js)")
    print("=" * 60)
    try:
        resp = requests.get(f"{BASE_URL}/static/app.js", timeout=10)
        ok = resp.status_code == 200 and "javascript" in resp.headers.get("Content-Type", "")
        content = resp.text
        js_checks = {
            "Has health check": "checkHealth" in content,
            "Has file validation": "validateFile" in content,
            "Has image preview": "showPreview" in content,
            "Has API call to /predict": '"/predict"' in content,
            "Has displayResults": "displayResults" in content,
            "Has error handling": "showError" in content,
            "Has tab switching": "tab" in content,
            "Has AbortController": "AbortController" in content,
        }
        all_ok = ok and all(js_checks.values())
        print(f"  {PASS if ok else FAIL} Status 200 with JavaScript MIME")
        print(f"  Content-Length: {len(content)} bytes")
        for name, c in js_checks.items():
            print(f"  {PASS if c else FAIL} {name}")
        results["STATIC_JS"] = PASS if all_ok else FAIL
        return all_ok
    except Exception as e:
        print(f"  Error: {e}")
        results["STATIC_JS"] = FAIL
        return False

def test_diseased_leaf():
    """Test 4: Predict with a diseased tomato leaf."""
    print("\n" + "=" * 60)
    print("TEST 4: Diseased Leaf Prediction (Tomato Early Blight)")
    print("=" * 60)
    img_path = get_first_image("Tomato___Early_blight")
    if not img_path:
        print("  SKIP: No test image found.")
        results["DISEASED_LEAF"] = "⚠️ SKIP"
        return False
    try:
        with open(img_path, "rb") as f:
            resp = requests.post(f"{BASE_URL}/predict", files={"file": (os.path.basename(img_path), f, "image/jpeg")}, timeout=30)
        data = resp.json()
        ok = resp.status_code == 200 and data.get("success") is True
        print(f"  Status: {resp.status_code}")
        print(f"  Success: {data.get('success')}")
        print(f"  Crop: {data.get('crop')}")
        print(f"  Disease: {data.get('disease')}")
        print(f"  Confidence: {data.get('confidence')}")
        print(f"  Low Confidence: {data.get('is_low_confidence')}")
        print(f"  Model: {data.get('model_version')}")
        if data.get("treatment"):
            print(f"  Treatment Status: {data['treatment'].get('status')}")
            print(f"  Has Symptoms: {bool(data['treatment'].get('symptoms'))}")
            print(f"  Has Safety Warning: {bool(data['treatment'].get('safety_warning'))}")
        results["DISEASED_LEAF"] = PASS if ok else FAIL
        return ok
    except Exception as e:
        print(f"  Error: {e}")
        results["DISEASED_LEAF"] = FAIL
        return False

def test_healthy_leaf():
    """Test 5: Predict with a healthy tomato leaf."""
    print("\n" + "=" * 60)
    print("TEST 5: Healthy Leaf Prediction (Tomato Healthy)")
    print("=" * 60)
    img_path = get_first_image("Tomato___healthy")
    if not img_path:
        print("  SKIP: No test image found.")
        results["HEALTHY_LEAF"] = "⚠️ SKIP"
        return False
    try:
        with open(img_path, "rb") as f:
            resp = requests.post(f"{BASE_URL}/predict", files={"file": (os.path.basename(img_path), f, "image/jpeg")}, timeout=30)
        data = resp.json()
        ok = resp.status_code == 200 and data.get("success") is True
        is_healthy = "healthy" in data.get("disease", "").lower()
        print(f"  Status: {resp.status_code}")
        print(f"  Success: {data.get('success')}")
        print(f"  Crop: {data.get('crop')}")
        print(f"  Disease: {data.get('disease')}")
        print(f"  Is Healthy: {is_healthy}")
        print(f"  Confidence: {data.get('confidence')}")
        print(f"  Model: {data.get('model_version')}")
        results["HEALTHY_LEAF"] = PASS if ok else FAIL
        return ok
    except Exception as e:
        print(f"  Error: {e}")
        results["HEALTHY_LEAF"] = FAIL
        return False

def test_potato_disease():
    """Test 6: Predict with a diseased potato leaf."""
    print("\n" + "=" * 60)
    print("TEST 6: Diseased Potato Leaf (Late Blight)")
    print("=" * 60)
    img_path = get_first_image("Potato___Late_blight")
    if not img_path:
        print("  SKIP: No test image found.")
        results["POTATO_DISEASE"] = "⚠️ SKIP"
        return False
    try:
        with open(img_path, "rb") as f:
            resp = requests.post(f"{BASE_URL}/predict", files={"file": (os.path.basename(img_path), f, "image/jpeg")}, timeout=30)
        data = resp.json()
        ok = resp.status_code == 200 and data.get("success") is True
        print(f"  Status: {resp.status_code}")
        print(f"  Success: {data.get('success')}")
        print(f"  Crop: {data.get('crop')}")
        print(f"  Disease: {data.get('disease')}")
        print(f"  Confidence: {data.get('confidence')}")
        print(f"  Model: {data.get('model_version')}")
        results["POTATO_DISEASE"] = PASS if ok else FAIL
        return ok
    except Exception as e:
        print(f"  Error: {e}")
        results["POTATO_DISEASE"] = FAIL
        return False

def test_unsupported_file():
    """Test 7: Upload non-image file (.txt)."""
    print("\n" + "=" * 60)
    print("TEST 7: Unsupported File (.txt)")
    print("=" * 60)
    try:
        fake_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        fake_file.write("This is not an image.")
        fake_file.close()
        with open(fake_file.name, "rb") as f:
            resp = requests.post(f"{BASE_URL}/predict", files={"file": ("test.txt", f, "text/plain")}, timeout=10)
        data = resp.json()
        ok = resp.status_code == 415 and data.get("success") is False
        print(f"  Status: {resp.status_code}")
        print(f"  Error Code: {data.get('error', {}).get('code')}")
        print(f"  Error Message: {data.get('error', {}).get('message')}")
        os.unlink(fake_file.name)
        results["UNSUPPORTED_FILE"] = PASS if ok else FAIL
        return ok
    except Exception as e:
        print(f"  Error: {e}")
        results["UNSUPPORTED_FILE"] = FAIL
        return False

def test_empty_file():
    """Test 8: Upload empty image file."""
    print("\n" + "=" * 60)
    print("TEST 8: Empty Image File")
    print("=" * 60)
    try:
        fake_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, mode="wb")
        fake_file.write(b"")
        fake_file.close()
        with open(fake_file.name, "rb") as f:
            resp = requests.post(f"{BASE_URL}/predict", files={"file": ("empty.jpg", f, "image/jpeg")}, timeout=10)
        data = resp.json()
        ok = resp.status_code == 400 and data.get("success") is False
        print(f"  Status: {resp.status_code}")
        print(f"  Error Code: {data.get('error', {}).get('code')}")
        print(f"  Error Message: {data.get('error', {}).get('message')}")
        os.unlink(fake_file.name)
        results["EMPTY_FILE"] = PASS if ok else FAIL
        return ok
    except Exception as e:
        print(f"  Error: {e}")
        results["EMPTY_FILE"] = FAIL
        return False

def test_corrupted_image():
    """Test 9: Upload corrupted image (invalid bytes with .jpg extension)."""
    print("\n" + "=" * 60)
    print("TEST 9: Corrupted Image File")
    print("=" * 60)
    try:
        fake_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, mode="wb")
        fake_file.write(b"this is definitely not a valid jpeg image file content at all")
        fake_file.close()
        with open(fake_file.name, "rb") as f:
            resp = requests.post(f"{BASE_URL}/predict", files={"file": ("corrupted.jpg", f, "image/jpeg")}, timeout=10)
        data = resp.json()
        ok = resp.status_code == 422 and data.get("success") is False
        print(f"  Status: {resp.status_code}")
        print(f"  Error Code: {data.get('error', {}).get('code')}")
        print(f"  Error Message: {data.get('error', {}).get('message')}")
        os.unlink(fake_file.name)
        results["CORRUPTED_IMAGE"] = PASS if ok else FAIL
        return ok
    except Exception as e:
        print(f"  Error: {e}")
        results["CORRUPTED_IMAGE"] = FAIL
        return False


def test_no_file():
    """Test 10: POST /predict without any file."""
    print("\n" + "=" * 60)
    print("TEST 10: Missing File Upload")
    print("=" * 60)
    try:
        resp = requests.post(f"{BASE_URL}/predict", timeout=10)
        data = resp.json()
        ok = resp.status_code == 400 and data.get("success") is False
        print(f"  Status: {resp.status_code}")
        print(f"  Error Code: {data.get('error', {}).get('code')}")
        print(f"  Error Message: {data.get('error', {}).get('message')}")
        results["MISSING_FILE"] = PASS if ok else FAIL
        return ok
    except Exception as e:
        print(f"  Error: {e}")
        results["MISSING_FILE"] = FAIL
        return False


if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║   AI Farmer Assistant — Frontend Integration Test Suite   ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    # Run all tests
    test_health()
    test_frontend_html()
    test_static_css()
    test_static_js()
    test_diseased_leaf()
    test_healthy_leaf()
    test_potato_disease()
    test_unsupported_file()
    test_empty_file()
    test_corrupted_image()
    test_no_file()

    # Final summary
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║               FINAL TEST RESULTS SUMMARY                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    for test_name, result in results.items():
        print(f"  {result}  {test_name}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r == PASS)
    failed = sum(1 for r in results.values() if r == FAIL)
    skipped = total - passed - failed
    
    print(f"\n  Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    
    if failed == 0:
        print("\n  🎉 ALL TESTS PASSED!")
    else:
        print(f"\n  ⚠️  {failed} TEST(S) FAILED!")
    
    sys.exit(0 if failed == 0 else 1)
