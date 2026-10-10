"""
Unit tests for the treatment recommendation module.
Validates:
1. Every supported disease in the model class mapping has an entry.
2. Unknown diseases are handled safely without exceptions.
3. Response schema is completely consistent.
4. No missing or null required fields.
5. Sourcing checks for agricultural credibility.
"""

import sys
import json
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.treatment import TreatmentAdvisor, get_treatment_recommendation

REQUIRED_FIELDS = [
    "status",
    "disease_key",
    "disease_name",
    "crop",
    "pathogen_or_cause",
    "symptoms",
    "preventive_measures",
    "cultural_practices",
    "organic_treatment",
    "chemical_treatment",
    "safety_warning",
    "source"
]

CREDIBLE_SOURCE_KEYWORDS = [
    "extension", "usda", "cornell", "uc ipm", "ifas", "penn state",
    "clemson", "ohio state", "fao", "purdue", "maryland", "texas a&m", "umass"
]


def run_treatment_tests():
    print("=" * 80)
    print("TREATMENT RECOMMENDATION MODULE TEST SUITE")
    print("=" * 80)

    test_results = {}
    advisor = TreatmentAdvisor()

    # 1. Load authoritative class mapping
    class_mapping_file = PROJECT_ROOT / "models" / "mobilenetv2" / "class_mapping.json"
    with open(class_mapping_file, "r") as f:
        class_mapping = json.load(f)

    expected_classes = sorted(list(class_mapping.keys()))
    print(f"\n[TEST 1] Verifying coverage for all {len(expected_classes)} supported dataset classes...")
    missing_classes = []
    
    for cname in expected_classes:
        res = advisor.get_treatment(cname)
        if res["status"] != "success":
            missing_classes.append(cname)
            print(f"   MISSING: {cname}")
        else:
            print(f"   PASS: [{res['crop']}] {res['disease_name']} ({cname})")

    coverage_ok = len(missing_classes) == 0
    print(f"   Diseases covered: {len(expected_classes) - len(missing_classes)}/{len(expected_classes)}")
    test_results["coverage"] = coverage_ok

    # 2. Unknown Disease Safety Handling
    print("\n[TEST 2] Verifying safe handling of unknown / malformed inputs...")
    unknown_inputs = [
        "Apple___scab",
        "Corn___common_rust",
        "Unknown_Crop___disease",
        "",
        None,
        "Tomato___Nonexistent_Wilt"
    ]
    unknown_safe = True

    for item in unknown_inputs:
        try:
            res = advisor.get_treatment(item)
            if res["status"] != "unknown_disease":
                unknown_safe = False
                print(f"   FAILED: Unexpected status for {item}: {res['status']}")
            # Check all required keys exist
            for f_name in REQUIRED_FIELDS:
                if f_name not in res:
                    unknown_safe = False
                    print(f"   FAILED: Missing field '{f_name}' in unknown fallback response for {item}")
        except Exception as e:
            unknown_safe = False
            print(f"   FAILED: Exception raised for input '{item}': {e}")

    print(f"   Unknown disease safety handling: {'PASS' if unknown_safe else 'FAIL'}")
    test_results["unknown_safety"] = unknown_safe

    # 3. Schema Consistency & Required Fields Check
    print("\n[TEST 3] Verifying schema consistency and required fields...")
    schema_ok = True

    for cname in expected_classes:
        res = advisor.get_treatment(cname)
        for req in REQUIRED_FIELDS:
            if req not in res:
                schema_ok = False
                print(f"   FAILED: Class '{cname}' missing required field: '{req}'")
            elif res[req] is None or res[req] == "":
                schema_ok = False
                print(f"   FAILED: Class '{cname}' has empty required field: '{req}'")

        # Type checks
        if not isinstance(res["symptoms"], list) or len(res["symptoms"]) == 0:
            schema_ok = False
            print(f"   FAILED: 'symptoms' must be non-empty list for '{cname}'")
        if not isinstance(res["preventive_measures"], list) or len(res["preventive_measures"]) == 0:
            schema_ok = False
            print(f"   FAILED: 'preventive_measures' must be non-empty list for '{cname}'")
        if not isinstance(res["cultural_practices"], list) or len(res["cultural_practices"]) == 0:
            schema_ok = False
            print(f"   FAILED: 'cultural_practices' must be non-empty list for '{cname}'")
        if not isinstance(res["organic_treatment"], list) or len(res["organic_treatment"]) == 0:
            schema_ok = False
            print(f"   FAILED: 'organic_treatment' must be non-empty list for '{cname}'")
        if not isinstance(res["chemical_treatment"], list) or len(res["chemical_treatment"]) == 0:
            schema_ok = False
            print(f"   FAILED: 'chemical_treatment' must be non-empty list for '{cname}'")
        if not isinstance(res["safety_warning"], str) or len(res["safety_warning"]) < 20:
            schema_ok = False
            print(f"   FAILED: 'safety_warning' too short or invalid for '{cname}'")

    print(f"   Schema consistency across all entries: {'PASS' if schema_ok else 'FAIL'}")
    test_results["schema_consistency"] = schema_ok

    # 4. Crop + Disease Explicit Mapping
    print("\n[TEST 4] Verifying (crop + disease) explicit mapping...")
    crop_disease_ok = True
    test_pairs = [
        ("Tomato", "Early Blight", "Tomato___Early_blight"),
        ("Potato", "Late Blight", "Potato___Late_blight"),
        ("Tomato", "Bacterial Spot", "Tomato___Bacterial_spot"),
        ("Tomato", "Leaf Mold", "Tomato___Leaf_Mold"),
        ("Potato", "healthy", "Potato___healthy"),
        ("Tomato", "Spider mites", "Tomato___Spider_mites Two-spotted_spider_mite"),
        ("Tomato", "Target Spot", "Tomato___Target_Spot"),
        ("Tomato", "Yellow Leaf Curl", "Tomato___Tomato_Yellow_Leaf_Curl_Virus"),
        ("Tomato", "Mosaic Virus", "Tomato___Tomato_mosaic_virus"),
    ]
    for crop, disease, expected_key in test_pairs:
        res = advisor.get_treatment_by_crop_and_disease(crop, disease)
        if res["status"] != "success" or res["disease_key"] != expected_key:
            crop_disease_ok = False
            print(f"   FAILED: ({crop}, {disease}) expected {expected_key}, got {res.get('disease_key')}")
        else:
            print(f"   PASS: ({crop}, {disease}) -> {expected_key}")

    print(f"   Crop + disease explicit mapping: {'PASS' if crop_disease_ok else 'FAIL'}")
    test_results["crop_disease_mapping"] = crop_disease_ok

    # 5. Credible Sourcing Check
    print("\n[TEST 5] Verifying agricultural authority sources...")
    sources_ok = True
    for cname in expected_classes:
        res = advisor.get_treatment(cname)
        source_str = res["source"].lower()
        has_credible_source = any(k in source_str for k in CREDIBLE_SOURCE_KEYWORDS)
        if not has_credible_source:
            sources_ok = False
            print(f"   WARNING: Class '{cname}' source might lack recognized extension keyword: '{res['source']}'")

    print(f"   Authoritative sources validated: {'PASS' if sources_ok else 'FAIL'}")
    test_results["sources"] = sources_ok

    # Summary
    all_passed = all(test_results.values())
    total_tests = len(test_results)
    passed_count = sum(1 for v in test_results.values() if v)

    print("\n" + "=" * 80)
    print(f"TREATMENT MODULE STATUS: {'PASS' if all_passed else 'FAIL'}")
    print("=" * 80)
    print(f"DISEASES COVERED: {len(expected_classes)}/13")
    print(f"MISSING ENTRIES: {len(missing_classes)}")
    print(f"SOURCE CHECK: {'PASS (All backed by University Extension / USDA / FAO)' if sources_ok else 'FAIL'}")
    print(f"TESTS PASSED: {passed_count}/{total_tests}")

    return all_passed, test_results


if __name__ == "__main__":
    passed, results = run_treatment_tests()
    sys.exit(0 if passed else 1)
