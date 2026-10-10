"""
Test suite for the disease classification inference module.
Tests:
1. Valid image (path, PIL, and bytes)
2. Invalid image (corrupted bytes)
3. Unsupported file (non-image, missing file)
4. Very small image (1x1 and 4x4 pixels)
5. Prediction response format
"""

import sys
import io
import json
import tempfile
from pathlib import Path
from PIL import Image

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference import DiseaseClassifier, InferenceError


def run_all_tests():
    print("=" * 80)
    print("DISEASE CLASSIFIER INFERENCE TEST SUITE")
    print("=" * 80)

    test_results = {}
    
    # 0. Model Loading Test
    print("\n[TEST 0] Initializing DiseaseClassifier...")
    try:
        classifier = DiseaseClassifier()
        print(f"   Model successfully loaded from: {classifier.model_path}")
        print(f"   Model version: {classifier.model_version}")
        print(f"   Number of classes: {classifier.num_classes}")
        test_results["model_loaded"] = True
    except Exception as e:
        print(f"   FAILED: Could not load model: {e}")
        test_results["model_loaded"] = False
        return False, test_results

    # 1. Valid Image Test
    print("\n[TEST 1] Valid Image Test...")
    test_img_dir = PROJECT_ROOT / "data" / "processed" / "tomato_potato_split" / "test"
    sample_images = list(test_img_dir.rglob("*.jpg"))
    if not sample_images:
        print("   FAILED: No test images found")
        test_results["valid_image"] = False
    else:
        sample_path = sample_images[0]
        
        # Test 1a: File path input
        res_path = classifier.predict(sample_path)
        print(f"   1a. File path input -> Disease: {res_path['disease']} (Conf: {res_path['confidence']}, Idx: {res_path['class_index']})")
        
        # Test 1b: PIL Image input
        pil_img = Image.open(sample_path)
        res_pil = classifier.predict(pil_img)
        print(f"   1b. PIL Image input -> Disease: {res_pil['disease']} (Conf: {res_pil['confidence']})")
        
        # Test 1c: Bytes input
        with open(sample_path, "rb") as f:
            raw_bytes = f.read()
        res_bytes = classifier.predict(raw_bytes)
        print(f"   1c. Raw Bytes input -> Disease: {res_bytes['disease']} (Conf: {res_bytes['confidence']})")

        valid_ok = (
            res_path["class_index"] >= 0 and res_path["confidence"] > 0 and
            res_pil["class_index"] == res_path["class_index"] and
            res_bytes["class_index"] == res_path["class_index"]
        )
        print(f"   Valid Image Test: {'PASS' if valid_ok else 'FAIL'}")
        test_results["valid_image"] = valid_ok

    # 2. Invalid Image Test (Corrupted bytes & Malformed file)
    print("\n[TEST 2] Invalid Image Test...")
    corrupt_bytes = b"NOT_A_VALID_JPEG_HEADER_GARBAGE_BYTES_123456789"
    
    # 2a: Safe prediction (should NOT crash)
    res_corrupt = classifier.predict(corrupt_bytes)
    print(f"   2a. Corrupted bytes handled safely: {res_corrupt}")
    corrupt_safe = (res_corrupt["class_index"] == -1 and "error" in res_corrupt and res_corrupt["confidence"] == 0.0)

    # 2b: Raising error when requested
    raised_as_expected = False
    try:
        classifier.predict(corrupt_bytes, raise_on_error=True)
    except InferenceError as e:
        raised_as_expected = True
        print(f"   2b. InferenceError raised as expected with message: {e}")

    # 2c: Empty byte buffer
    res_empty = classifier.predict(b"")
    empty_safe = (res_empty["class_index"] == -1 and "error" in res_empty)
    print(f"   2c. Empty bytes handled safely: {res_empty['error']}")

    invalid_ok = corrupt_safe and raised_as_expected and empty_safe
    print(f"   Invalid Image Test: {'PASS' if invalid_ok else 'FAIL'}")
    test_results["invalid_image"] = invalid_ok

    # 3. Unsupported / Missing File Test
    print("\n[TEST 3] Unsupported File & Missing Path Test...")
    # 3a: Non-existent path
    res_missing = classifier.predict(PROJECT_ROOT / "non_existent_file_xyz123.jpg")
    print(f"   3a. Non-existent path handled safely: {res_missing['error']}")
    missing_ok = (res_missing["class_index"] == -1 and "error" in res_missing)

    # 3b: Text file with .txt extension
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as tf:
        tf.write("Just some random text contents that are not an image.")
        temp_txt_path = Path(tf.name)
    
    res_txt = classifier.predict(temp_txt_path)
    print(f"   3b. Text file handled safely: {res_txt['error']}")
    txt_ok = (res_txt["class_index"] == -1 and "error" in res_txt)
    temp_txt_path.unlink()

    unsupported_ok = missing_ok and txt_ok
    print(f"   Unsupported File Test: {'PASS' if unsupported_ok else 'FAIL'}")
    test_results["unsupported_file"] = unsupported_ok

    # 4. Very Small Image Test
    print("\n[TEST 4] Very Small Image Test (1x1 and 4x4 pixels)...")
    # 1x1 image
    img_1x1 = Image.new("RGB", (1, 1), color=(34, 139, 34))  # Forest green
    res_1x1 = classifier.predict(img_1x1)
    print(f"   4a. 1x1 image -> Disease: {res_1x1['disease']} (Confidence: {res_1x1['confidence']}, Idx: {res_1x1['class_index']})")
    
    # 4x4 image
    img_4x4 = Image.new("RGB", (4, 4), color=(139, 69, 19))   # Brown
    res_4x4 = classifier.predict(img_4x4)
    print(f"   4b. 4x4 image -> Disease: {res_4x4['disease']} (Confidence: {res_4x4['confidence']}, Idx: {res_4x4['class_index']})")

    small_ok = (
        res_1x1["class_index"] in range(classifier.num_classes) and res_1x1["confidence"] > 0 and
        res_4x4["class_index"] in range(classifier.num_classes) and res_4x4["confidence"] > 0
    )
    print(f"   Very Small Image Test: {'PASS' if small_ok else 'FAIL'}")
    test_results["small_image"] = small_ok

    # 5. Prediction Response Format Verification
    print("\n[TEST 5] Prediction Response Format Verification...")
    required_keys = {"disease", "confidence", "class_index", "model_version"}
    res = classifier.predict(sample_path)
    
    keys_present = required_keys.issubset(res.keys())
    types_correct = (
        isinstance(res["disease"], str) and
        isinstance(res["confidence"], float) and
        isinstance(res["class_index"], int) and
        isinstance(res["model_version"], str)
    )
    conf_in_range = 0.0 <= res["confidence"] <= 1.0
    idx_in_range = 0 <= res["class_index"] < classifier.num_classes

    # Ensure JSON serializable
    try:
        json_str = json.dumps(res)
        json_serializable = True
    except Exception:
        json_serializable = False

    format_ok = keys_present and types_correct and conf_in_range and idx_in_range and json_serializable
    print(f"   Required keys present: {keys_present}")
    print(f"   Types correct: {types_correct}")
    print(f"   Confidence in [0, 1]: {conf_in_range}")
    print(f"   Class index in range [0, {classifier.num_classes - 1}]: {idx_in_range}")
    print(f"   JSON serializable: {json_serializable}")
    print(f"   Prediction Response Format Test: {'PASS' if format_ok else 'FAIL'}")
    test_results["response_format"] = format_ok

    # Summary
    all_passed = all(test_results.values())
    total_tests = len(test_results)
    passed_count = sum(1 for v in test_results.values() if v)

    print("\n" + "=" * 80)
    print(f"INFERENCE STATUS: {'PASS' if all_passed else 'FAIL'}")
    print("=" * 80)
    print(f"MODEL LOADED: {'PASS' if test_results.get('model_loaded') else 'FAIL'}")
    print(f"VALID IMAGE TEST: {'PASS' if test_results.get('valid_image') else 'FAIL'}")
    print(f"INVALID IMAGE TEST: {'PASS' if test_results.get('invalid_image') else 'FAIL'}")
    print(f"OUTPUT FORMAT: {'PASS' if test_results.get('response_format') else 'FAIL'}")
    print(f"ERROR HANDLING: {'PASS' if test_results.get('unsupported_file') else 'FAIL'}")
    print(f"TESTS PASSED: {passed_count}/{total_tests}")

    return all_passed, test_results


if __name__ == "__main__":
    passed, results = run_all_tests()
    sys.exit(0 if passed else 1)
