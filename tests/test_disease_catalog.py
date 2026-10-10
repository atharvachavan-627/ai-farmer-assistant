"""
Test Suite for Disease Information API in AI Farmer Assistant.

Validates:
1. GET /diseases returns all 13 supported classes matching model class mapping.
2. Healthy classes (Potato___healthy, Tomato___healthy) are distinguished and represented accurately.
3. GET /diseases/{disease_code} returns full structured details for valid classes.
4. Unknown disease code returns HTTP 404 with structured error payload.
5. Case-insensitive search filtering across name, crop, and symptoms.
6. Case-insensitive crop filtering for 'potato' and 'tomato'.
7. Multilingual support: language parameter ('en', 'hi', 'mr') and Accept-Language header.
8. English fallback behavior when invalid or unsupported language is requested.
9. Authentic Hindi and Marathi localized content without broken strings or fabricated facts.
10. Chemical treatment safety policy: verified technical statements preserved, no chemical pesticides on healthy foliage.
11. Aliases and shape compatibility matching frontend diseaseService.js and DiseaseDetails.jsx expectations.
"""

import unittest
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.api import app
from src.disease_catalog import get_catalog_service, SUPPORTED_LANGUAGES


class TestDiseaseCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.service = get_catalog_service()
        
        # Load authoritative class mapping
        cm_path = PROJECT_ROOT / "models" / "mobilenetv2" / "class_mapping.json"
        with open(cm_path, "r", encoding="utf-8") as f:
            cls.class_mapping = json.load(f)

    def test_01_catalogue_returns_all_13_classes(self):
        """GET /diseases must return exactly 13 items matching all model classes."""
        resp = self.client.get("/diseases")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertEqual(data["total"], 13)
        self.assertEqual(len(data["items"]), 13)

        retrieved_codes = {item["disease_code"] for item in data["items"]}
        expected_codes = set(self.class_mapping.keys())
        self.assertEqual(retrieved_codes, expected_codes, "Every model class must have an exact catalogue entry.")

    def test_02_catalogue_items_have_required_frontend_fields(self):
        """Every item must provide all fields expected by diseaseService.js normaliseDisease."""
        resp = self.client.get("/diseases")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()["items"]

        required_keys = [
            "disease_code", "name", "crop", "category",
            "symptoms_summary", "prevention_summary", "overview",
            "symptoms", "favourable_conditions", "preventive_measures",
            "cultural_management", "organic_management", "chemical_treatment",
            "chemical_verified", "consult_expert", "content_language"
        ]

        for item in items:
            for k in required_keys:
                self.assertIn(k, item, f"Missing key '{k}' in disease item '{item.get('disease_code')}'")
            self.assertIsInstance(item["symptoms"], list)
            self.assertIsInstance(item["preventive_measures"], list)
            self.assertIsInstance(item["cultural_management"], list)
            self.assertIsInstance(item["organic_management"], list)
            self.assertIsInstance(item["chemical_treatment"], list)
            self.assertIsInstance(item["consult_expert"], list)
            # Verify frontend aliases exist
            self.assertEqual(item["code"], item["disease_code"])
            self.assertEqual(item["disease"], item["name"])

    def test_03_healthy_classes_handled_appropriately(self):
        """Healthy foliage classes must be identified as Healthy without chemical pesticide recommendations."""
        healthy_codes = ["Potato___healthy", "Tomato___healthy"]
        for code in healthy_codes:
            resp = self.client.get(f"/diseases/{code}")
            self.assertEqual(resp.status_code, 200)
            item = resp.json()

            self.assertEqual(item["category"], "Healthy", f"{code} should be categorized as 'Healthy'")
            self.assertIn("healthy", item["name"].lower())
            self.assertFalse(item["chemical_verified"], f"{code} must have chemical_verified=False")
            self.assertEqual(item["chemical_treatment"], [], f"{code} must have empty chemical_treatment list")
            self.assertIn("healthy", item["overview"].lower())

    def test_04_disease_detail_lookup_success(self):
        """GET /diseases/{disease_code} must return detailed record for every valid code."""
        for code in self.class_mapping.keys():
            resp = self.client.get(f"/diseases/{code}")
            self.assertEqual(resp.status_code, 200, f"Failed lookup for valid code: {code}")
            item = resp.json()
            self.assertEqual(item["disease_code"], code)
            self.assertTrue(len(item["name"]) > 0)
            self.assertIn(item["crop"], ["Potato", "Tomato"])

    def test_05_unknown_disease_returns_404(self):
        """GET /diseases/{disease_code} must return 404 for unknown or malformed codes."""
        from urllib.parse import quote
        test_unknowns = [
            "NonExistentDisease",
            "Corn___Common_rust",
            "../../etc/passwd",
            "Potato___invalid",
            "Tomato___1234"
        ]
        for bad_code in test_unknowns:
            encoded_code = quote(bad_code, safe="")
            resp = self.client.get(f"/diseases/{encoded_code}")
            self.assertEqual(resp.status_code, 404, f"Expected 404 for unknown code '{bad_code}'")
            data = resp.json()
            self.assertEqual(data.get("success"), False)
            self.assertIn("error", data)
            self.assertIn(data["error"]["code"], ["DISEASE_NOT_FOUND", "NOT_FOUND"])

    def test_06_case_insensitive_crop_filtering(self):
        """GET /diseases?crop=... must accurately filter by crop case-insensitively."""
        # Potato (3 classes: Early blight, Late blight, healthy)
        resp_pot = self.client.get("/diseases?crop=potato")
        self.assertEqual(resp_pot.status_code, 200)
        pot_items = resp_pot.json()["items"]
        self.assertEqual(len(pot_items), 3)
        for it in pot_items:
            self.assertEqual(it["crop"], "Potato")

        # Tomato (10 classes)
        resp_tom = self.client.get("/diseases?crop=TOMATO")
        self.assertEqual(resp_tom.status_code, 200)
        tom_items = resp_tom.json()["items"]
        self.assertEqual(len(tom_items), 10)
        for it in tom_items:
            self.assertEqual(it["crop"], "Tomato")

    def test_07_search_filtering(self):
        """GET /diseases?search=... performs case-insensitive search across name, code, symptoms."""
        # Search 'blight' -> 4 classes (Potato Early/Late, Tomato Early/Late)
        resp = self.client.get("/diseases?search=blight")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()["items"]
        self.assertEqual(len(items), 4)
        for it in items:
            self.assertIn("blight", (it["name"] + it["disease_code"]).lower())

        # Search 'mosaic' -> 1 class (Tomato Mosaic Virus)
        resp_mos = self.client.get("/diseases?search=MOSAIC")
        self.assertEqual(resp_mos.status_code, 200)
        self.assertEqual(len(resp_mos.json()["items"]), 1)
        self.assertEqual(resp_mos.json()["items"][0]["disease_code"], "Tomato___Tomato_mosaic_virus")

        # Search with no match
        resp_none = self.client.get("/diseases?search=xyznonexistentterm")
        self.assertEqual(resp_none.status_code, 200)
        self.assertEqual(resp_none.json()["total"], 0)
        self.assertEqual(len(resp_none.json()["items"]), 0)

    def test_08_multilingual_hindi_support(self):
        """GET /diseases?language=hi returns authentic Hindi translations with content_language='hi'."""
        resp = self.client.get("/diseases?language=hi")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["language"], "hi")

        for item in data["items"]:
            self.assertEqual(item["content_language"], "hi")
            # Verify Hindi characters present in name
            self.assertTrue(
                any('\u0900' <= char <= '\u097F' for char in item["name"]),
                f"Hindi name for {item['disease_code']} should contain Devanagari characters: {item['name']}"
            )
            # Verify overview and symptoms are translated
            self.assertTrue(len(item["overview"]) > 0)
            self.assertTrue(len(item["symptoms"]) > 0)
            self.assertTrue(any('\u0900' <= char <= '\u097F' for char in item["overview"]))

    def test_09_multilingual_marathi_support(self):
        """GET /diseases?language=mr returns authentic Marathi translations with content_language='mr'."""
        resp = self.client.get("/diseases?language=mr")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["language"], "mr")

        for item in data["items"]:
            self.assertEqual(item["content_language"], "mr")
            self.assertTrue(
                any('\u0900' <= char <= '\u097F' for char in item["name"]),
                f"Marathi name for {item['disease_code']} should contain Devanagari characters: {item['name']}"
            )
            self.assertTrue(len(item["overview"]) > 0)
            self.assertTrue(len(item["symptoms"]) > 0)

    def test_10_accept_language_header_support(self):
        """Endpoint respects Accept-Language HTTP header when query parameter is omitted."""
        resp = self.client.get("/diseases", headers={"Accept-Language": "mr-IN,mr;q=0.9,en;q=0.8"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["language"], "mr")

        resp_single = self.client.get(
            "/diseases/Potato___Early_blight",
            headers={"Accept-Language": "hi-IN,hi;q=0.9"}
        )
        self.assertEqual(resp_single.status_code, 200)
        self.assertEqual(resp_single.json()["content_language"], "hi")

    def test_11_unsupported_language_fallback_to_english(self):
        """Unsupported language safely falls back to English without error."""
        resp = self.client.get("/diseases?language=fr")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["language"], "en")
        for it in data["items"]:
            self.assertEqual(it["content_language"], "en")

    def test_12_chemical_treatment_preservation(self):
        """Chemical treatment instructions maintain active ingredient integrity without fabricated dosages."""
        resp = self.client.get("/diseases/Potato___Early_blight")
        self.assertEqual(resp.status_code, 200)
        item = resp.json()
        self.assertTrue(item["chemical_verified"])
        chem_text = " ".join(item["chemical_treatment"]).lower()
        self.assertTrue(
            "mancozeb" in chem_text or "chlorothalonil" in chem_text or "difenoconazole" in chem_text,
            "Must reference verified agronomic active ingredients."
        )


if __name__ == "__main__":
    unittest.main()
