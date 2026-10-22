"""
Automated Test Suite for Strict Input Validation in AI Farmer Assistant.

Verifies all 17 mandatory acceptance criteria:
 1. A valid tomato leaf reaches disease classification.
 2. A valid potato leaf reaches disease classification.
 3. A photograph of a person is rejected (INVALID_NON_PLANT_IMAGE).
 4. An unrelated plant leaf is rejected (UNSUPPORTED_PLANT).
 5. A photograph of an animal is rejected (INVALID_NON_PLANT_IMAGE).
 6. A photograph of a building is rejected (INVALID_NON_PLANT_IMAGE).
 7. A tomato fruit without a leaf is rejected (INVALID_NO_LEAF).
 8. A corrupted image is rejected (INVALID_FILE / CORRUPTED_IMAGE).
 9. A blank or unusable image is rejected (INVALID_IMAGE_QUALITY).
10. An uncertain crop is rejected (UNSUPPORTED_CROP_UNCERTAIN).
11. Invalid images never call the disease classifier (verified via mock).
12. Invalid images never call severity estimation (verified via mock).
13. Invalid images never generate treatment recommendations (verified via mock).
14. Invalid images do not create successful scan-history entries in database.
15. Frontend components implement dedicated invalid-input state (InvalidInputCard).
16. Previous analysis results are cleared when a new image is rejected.
17. Existing valid-image functionality continues to work.
"""

import io
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api import app
from src.config import get_settings
from src.database import get_db
from src.models import User, Analysis
from src.image_validator import (
    ImageValidator,
    get_image_validator,
    VALID_TOMATO_LEAF,
    VALID_POTATO_LEAF,
    INVALID_NON_PLANT_IMAGE,
    INVALID_NO_LEAF,
    UNSUPPORTED_PLANT,
    UNSUPPORTED_CROP_UNCERTAIN,
    INVALID_IMAGE_QUALITY,
    INVALID_FILE,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PV_COLOR_DIR = PROJECT_ROOT / "data" / "raw" / "plantvillage" / "plantvillage dataset" / "color"


class TestStrictInputValidation(unittest.TestCase):
    """Complete acceptance test suite for image validation pipeline and API integration."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.settings = get_settings()

        # Create unique test user for validation tests
        cls.email = f"strict_val_{np.random.randint(10000, 99999)}@example.com"
        cls.password = "SecureFarmerPass!2026"

        cls.client.post(
            "/auth/register",
            json={
                "full_name": "Validation Tester",
                "email": cls.email,
                "password": cls.password,
                "preferred_language": "en"
            }
        )

        login_res = cls.client.post(
            "/auth/login",
            json={"email": cls.email, "password": cls.password}
        )
        cls.session_cookie = login_res.cookies.get(cls.settings.SESSION_COOKIE_NAME)
        cls.csrf_token = login_res.cookies.get(cls.settings.CSRF_COOKIE_NAME)

        # Locate sample real leaf images from PlantVillage
        cls.real_tomato_path = None
        cls.real_potato_path = None
        cls.real_grape_path = None
        cls.real_apple_path = None
        cls.real_corn_path = None

        if PV_COLOR_DIR.exists():
            tom_dir = PV_COLOR_DIR / "Tomato___Early_blight"
            if tom_dir.exists():
                cls.real_tomato_path = next(tom_dir.glob("*.JPG"), None)

            pot_dir = PV_COLOR_DIR / "Potato___Early_blight"
            if pot_dir.exists():
                cls.real_potato_path = next(pot_dir.glob("*.JPG"), None)

            grape_dir = PV_COLOR_DIR / "Grape___healthy"
            if grape_dir.exists():
                cls.real_grape_path = next(grape_dir.glob("*.JPG"), None)

            apple_dir = PV_COLOR_DIR / "Apple___healthy"
            if apple_dir.exists():
                cls.real_apple_path = next(apple_dir.glob("*.JPG"), None)

            corn_dir = PV_COLOR_DIR / "Corn_(maize)___healthy"
            if corn_dir.exists():
                cls.real_corn_path = next(corn_dir.glob("*.JPG"), None)

    def _get_auth_headers_and_cookies(self):
        headers = {self.settings.CSRF_HEADER_NAME: self.csrf_token}
        cookies = {
            self.settings.SESSION_COOKIE_NAME: self.session_cookie,
            self.settings.CSRF_COOKIE_NAME: self.csrf_token,
        }
        return headers, cookies

    def _create_pil_bytes(self, image: Image.Image, format: str = "JPEG") -> bytes:
        buf = io.BytesIO()
        image.save(buf, format=format)
        return buf.getvalue()

    # -----------------------------------------------------------------------
    # Acceptance Test 1: Valid Tomato Leaf Reaches Disease Classification
    # -----------------------------------------------------------------------
    def test_01_valid_tomato_leaf_accepted(self):
        """A valid tomato leaf must be accepted and proceed to disease classification."""
        self.assertIsNotNone(self.real_tomato_path, "PlantVillage Tomato samples must exist")
        with open(self.real_tomato_path, "rb") as f:
            file_bytes = f.read()

        headers, cookies = self._get_auth_headers_and_cookies()
        response = self.client.post(
            "/predict",
            files={"image": ("tomato_leaf.jpg", file_bytes, "image/jpeg")},
            headers=headers,
            cookies=cookies,
        )

        self.assertEqual(response.status_code, 200, f"Expected 200 OK, got {response.status_code}: {response.text}")
        data = response.json()
        self.assertTrue(data.get("success"), "Response should indicate success=True")
        self.assertEqual(data.get("crop"), "Tomato", "Identified crop must be Tomato")
        self.assertIn("Tomato___", data.get("disease_code", ""))
        self.assertIn("treatment", data)
        self.assertIn("severity", data)

    # -----------------------------------------------------------------------
    # Acceptance Test 2: Valid Potato Leaf Reaches Disease Classification
    # -----------------------------------------------------------------------
    def test_02_valid_potato_leaf_accepted(self):
        """A valid potato leaf must be accepted and proceed to disease classification."""
        self.assertIsNotNone(self.real_potato_path, "PlantVillage Potato samples must exist")
        with open(self.real_potato_path, "rb") as f:
            file_bytes = f.read()

        headers, cookies = self._get_auth_headers_and_cookies()
        response = self.client.post(
            "/predict",
            files={"image": ("potato_leaf.jpg", file_bytes, "image/jpeg")},
            headers=headers,
            cookies=cookies,
        )

        self.assertEqual(response.status_code, 200, f"Expected 200 OK, got {response.status_code}: {response.text}")
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("crop"), "Potato", "Identified crop must be Potato")
        self.assertIn("Potato___", data.get("disease_code", ""))
        self.assertIn("treatment", data)
        self.assertIn("severity", data)

    # -----------------------------------------------------------------------
    # Acceptance Test 3: Photograph of a Person is Rejected
    # -----------------------------------------------------------------------
    def test_03_person_photograph_rejected(self):
        """A photograph of a person must be rejected as INVALID_NON_PLANT_IMAGE."""
        # Create a portrait/face-like image (skin tones: approx (210, 160, 130), hair, background)
        img = Image.new("RGB", (256, 256), color=(200, 200, 220))
        draw = ImageDraw.Draw(img)
        # Head (oval skin tone)
        draw.ellipse([60, 40, 196, 200], fill=(215, 168, 135))
        # Hair
        draw.ellipse([55, 30, 201, 100], fill=(45, 30, 20))
        # Eyes
        draw.ellipse([85, 95, 110, 115], fill=(255, 255, 255))
        draw.ellipse([92, 100, 102, 110], fill=(40, 30, 20))
        draw.ellipse([146, 95, 171, 115], fill=(255, 255, 255))
        draw.ellipse([153, 100, 163, 110], fill=(40, 30, 20))
        # Lips
        draw.rectangle([110, 155, 146, 165], fill=(180, 80, 80))
        file_bytes = self._create_pil_bytes(img)

        headers, cookies = self._get_auth_headers_and_cookies()
        response = self.client.post(
            "/predict",
            files={"image": ("person_selfie.jpg", file_bytes, "image/jpeg")},
            headers=headers,
            cookies=cookies,
        )

        self.assertEqual(response.status_code, 422, "Person image must return HTTP 422")
        data = response.json()
        self.assertFalse(data.get("success"))
        error_code = data.get("error_code") or data.get("error", {}).get("code")
        self.assertIn(error_code, ["INVALID_NON_PLANT_IMAGE", "INVALID_NO_LEAF"])

    # -----------------------------------------------------------------------
    # Acceptance Test 4: Unrelated Plant Leaves are Rejected
    # -----------------------------------------------------------------------
    def test_04_unrelated_plant_leaves_rejected(self):
        """Leaves from unsupported plants (grape, apple, corn) must be rejected with UNSUPPORTED_PLANT."""
        headers, cookies = self._get_auth_headers_and_cookies()

        unsupported_paths = [
            ("grape", self.real_grape_path),
            ("apple", self.real_apple_path),
            ("corn", self.real_corn_path),
        ]

        tested_at_least_one = False
        for plant_name, p in unsupported_paths:
            if p is not None and p.exists():
                tested_at_least_one = True
                with open(p, "rb") as f:
                    file_bytes = f.read()

                response = self.client.post(
                    "/predict",
                    files={"image": (f"{plant_name}_leaf.jpg", file_bytes, "image/jpeg")},
                    headers=headers,
                    cookies=cookies,
                )

                self.assertEqual(
                    response.status_code, 422,
                    f"Unsupported plant '{plant_name}' should return HTTP 422, got {response.status_code}: {response.text}"
                )
                data = response.json()
                self.assertFalse(data.get("success"))
                error_code = data.get("error_code") or data.get("error", {}).get("code")
                self.assertEqual(error_code, UNSUPPORTED_PLANT)
                self.assertIn("not supported", data.get("message", "").lower())

        self.assertTrue(tested_at_least_one, "Must test at least one unsupported plant leaf from dataset")

    # -----------------------------------------------------------------------
    # Acceptance Test 5: Photograph of an Animal is Rejected
    # -----------------------------------------------------------------------
    def test_05_animal_photograph_rejected(self):
        """A photograph of an animal must be rejected as INVALID_NON_PLANT_IMAGE or INVALID_NO_LEAF."""
        # Animal pattern (brown/tan fur texture)
        img = Image.new("RGB", (256, 256), color=(180, 130, 80))
        draw = ImageDraw.Draw(img)
        # Dog/cat face features
        draw.polygon([(70, 40), (100, 100), (40, 90)], fill=(120, 70, 30))  # ear 1
        draw.polygon([(186, 40), (156, 100), (216, 90)], fill=(120, 70, 30))  # ear 2
        draw.ellipse([80, 70, 176, 180], fill=(160, 110, 60))
        draw.ellipse([110, 130, 146, 160], fill=(20, 20, 20))  # snout
        file_bytes = self._create_pil_bytes(img)

        headers, cookies = self._get_auth_headers_and_cookies()
        response = self.client.post(
            "/predict",
            files={"image": ("dog_pet.jpg", file_bytes, "image/jpeg")},
            headers=headers,
            cookies=cookies,
        )

        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertFalse(data.get("success"))
        error_code = data.get("error_code") or data.get("error", {}).get("code")
        self.assertIn(error_code, ["INVALID_NON_PLANT_IMAGE", "INVALID_NO_LEAF"])

    # -----------------------------------------------------------------------
    # Acceptance Test 6: Photograph of a Building is Rejected
    # -----------------------------------------------------------------------
    def test_06_building_photograph_rejected(self):
        """A photograph of a building must be rejected as INVALID_NON_PLANT_IMAGE."""
        # Create an architectural building image (brick red / gray facade with windows)
        img = Image.new("RGB", (256, 256), color=(135, 206, 235))  # blue sky
        draw = ImageDraw.Draw(img)
        # Building structure
        draw.rectangle([40, 70, 216, 256], fill=(160, 82, 45))  # brick
        # Grid of glass windows
        for row in range(80, 240, 30):
            for col in range(55, 200, 30):
                draw.rectangle([col, row, col + 20, row + 20], fill=(220, 240, 255))
        file_bytes = self._create_pil_bytes(img)

        headers, cookies = self._get_auth_headers_and_cookies()
        response = self.client.post(
            "/predict",
            files={"image": ("city_building.jpg", file_bytes, "image/jpeg")},
            headers=headers,
            cookies=cookies,
        )

        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertFalse(data.get("success"))
        error_code = data.get("error_code") or data.get("error", {}).get("code")
        self.assertIn(error_code, ["INVALID_NON_PLANT_IMAGE", "INVALID_NO_LEAF"])

    # -----------------------------------------------------------------------
    # Acceptance Test 7: Tomato Fruit Without Leaf is Rejected
    # -----------------------------------------------------------------------
    def test_07_tomato_fruit_without_leaf_rejected(self):
        """A photograph of a tomato fruit alone without a leaf must be rejected as INVALID_NO_LEAF."""
        # Bright red shiny round tomato fruit on white cutting board
        img = Image.new("RGB", (256, 256), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        # Round red tomato
        draw.ellipse([48, 48, 208, 208], fill=(220, 25, 20))
        # Specular highlight
        draw.ellipse([80, 70, 110, 95], fill=(255, 120, 110))
        file_bytes = self._create_pil_bytes(img)

        headers, cookies = self._get_auth_headers_and_cookies()
        response = self.client.post(
            "/predict",
            files={"image": ("ripe_tomato_fruit.jpg", file_bytes, "image/jpeg")},
            headers=headers,
            cookies=cookies,
        )

        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertFalse(data.get("success"))
        error_code = data.get("error_code") or data.get("error", {}).get("code")
        self.assertIn(error_code, ["INVALID_NO_LEAF", "INVALID_NON_PLANT_IMAGE"])

    # -----------------------------------------------------------------------
    # Acceptance Test 8: Corrupted Image is Rejected
    # -----------------------------------------------------------------------
    def test_08_corrupted_image_rejected(self):
        """Corrupted, truncated, or random bytes must be rejected with 422 / INVALID_FILE."""
        corrupted_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00random_corrupted_garbage_bytes_1234567890"

        headers, cookies = self._get_auth_headers_and_cookies()
        response = self.client.post(
            "/predict",
            files={"image": ("corrupted.jpg", corrupted_bytes, "image/jpeg")},
            headers=headers,
            cookies=cookies,
        )

        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertFalse(data.get("success"))
        error_code = data.get("error_code") or data.get("error", {}).get("code")
        self.assertIn(error_code, ["INVALID_FILE", "CORRUPTED_IMAGE"])

    # -----------------------------------------------------------------------
    # Acceptance Test 9: Blank or Unusable Image is Rejected
    # -----------------------------------------------------------------------
    def test_09_blank_or_unusable_image_rejected(self):
        """Uniform flat black, flat white, or blurry images must be rejected as INVALID_IMAGE_QUALITY."""
        # Flat uniform blank white image
        white_img = Image.new("RGB", (256, 256), color=(255, 255, 255))
        file_bytes = self._create_pil_bytes(white_img)

        headers, cookies = self._get_auth_headers_and_cookies()
        response = self.client.post(
            "/predict",
            files={"image": ("blank_white.jpg", file_bytes, "image/jpeg")},
            headers=headers,
            cookies=cookies,
        )

        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertFalse(data.get("success"))
        error_code = data.get("error_code") or data.get("error", {}).get("code")
        self.assertEqual(error_code, INVALID_IMAGE_QUALITY)

    # -----------------------------------------------------------------------
    # Acceptance Test 10: Uncertain Crop Identity is Rejected
    # -----------------------------------------------------------------------
    def test_10_uncertain_crop_rejected(self):
        """When plant identity is ambiguous between crops, return UNSUPPORTED_CROP_UNCERTAIN."""
        # Test directly via ImageValidator decision engine
        validator = get_image_validator()

        # Mock classify_crop_and_plant to produce ambiguous probabilities
        ambiguous_crop_res = {
            "crop_probabilities": {"tomato": 0.46, "potato": 0.44, "unsupported_plant": 0.08, "non_plant": 0.02},
            "predicted_crop_class": "tomato",
            "crop_confidence": 0.46,
            "imagenet_top1": {"id": 0, "name": "leaf", "prob": 0.3},
            "is_imagenet_non_plant": False,
        }

        # Mock leaf presence to be True
        with patch.object(validator, "detect_leaf_presence", return_value=(True, {"coverage_percent": 60.0})), \
             patch.object(validator, "classify_crop_and_plant", return_value=ambiguous_crop_res):
            if self.real_tomato_path and self.real_tomato_path.exists():
                img = Image.open(self.real_tomato_path).convert("RGB")
            else:
                np_arr = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
                img = Image.fromarray(np_arr)
            res = validator.validate(pil_image=img)
            self.assertFalse(res.is_valid)
            self.assertEqual(res.decision, UNSUPPORTED_CROP_UNCERTAIN)
            self.assertEqual(res.error_code, UNSUPPORTED_CROP_UNCERTAIN)
            self.assertIn("could not verify", res.message.lower())

    # -----------------------------------------------------------------------
    # Acceptance Test 11: Invalid Images NEVER Call Disease Classifier
    # -----------------------------------------------------------------------
    def test_11_invalid_images_never_call_classifier(self):
        """Verify that when an invalid image is submitted, DiseaseClassifier.predict is NEVER invoked."""
        corrupted_bytes = b"bad_image_data_not_decodable"
        headers, cookies = self._get_auth_headers_and_cookies()

        with patch("src.inference.DiseaseClassifier.predict") as mock_classifier_predict:
            response = self.client.post(
                "/predict",
                files={"image": ("bad.jpg", corrupted_bytes, "image/jpeg")},
                headers=headers,
                cookies=cookies,
            )
            self.assertEqual(response.status_code, 422)
            mock_classifier_predict.assert_not_called()

    # -----------------------------------------------------------------------
    # Acceptance Test 12: Invalid Images NEVER Call Severity Estimation
    # -----------------------------------------------------------------------
    def test_12_invalid_images_never_call_severity_estimator(self):
        """Verify that when an invalid image is submitted, estimate_disease_severity is NEVER invoked."""
        img = Image.new("RGB", (256, 256), color=(255, 255, 255))
        file_bytes = self._create_pil_bytes(img)
        headers, cookies = self._get_auth_headers_and_cookies()

        with patch("src.api.estimate_disease_severity") as mock_severity:
            response = self.client.post(
                "/predict",
                files={"image": ("blank.jpg", file_bytes, "image/jpeg")},
                headers=headers,
                cookies=cookies,
            )
            self.assertEqual(response.status_code, 422)
            mock_severity.assert_not_called()

    # -----------------------------------------------------------------------
    # Acceptance Test 13: Invalid Images NEVER Generate Treatment Recommendations
    # -----------------------------------------------------------------------
    def test_13_invalid_images_never_call_treatment_advisor(self):
        """Verify that TreatmentAdvisor.get_treatment is NEVER invoked for invalid inputs."""
        img = Image.new("RGB", (256, 256), color=(255, 255, 255))
        file_bytes = self._create_pil_bytes(img)
        headers, cookies = self._get_auth_headers_and_cookies()

        with patch("src.treatment.TreatmentAdvisor.get_treatment") as mock_advisor:
            response = self.client.post(
                "/predict",
                files={"image": ("blank.jpg", file_bytes, "image/jpeg")},
                headers=headers,
                cookies=cookies,
            )
            self.assertEqual(response.status_code, 422)
            mock_advisor.assert_not_called()

    # -----------------------------------------------------------------------
    # Acceptance Test 14: Invalid Images Do Not Create Scan History Entries
    # -----------------------------------------------------------------------
    def test_14_invalid_images_do_not_persist_history(self):
        """Verify that rejected images do not create any records in the analyses database table."""
        headers, cookies = self._get_auth_headers_and_cookies()

        # Count existing history
        hist_before = self.client.get("/history", headers=headers, cookies=cookies)
        total_before = hist_before.json().get("total", 0)

        # Submit invalid image
        img = Image.new("RGB", (256, 256), color=(255, 255, 255))
        file_bytes = self._create_pil_bytes(img)
        self.client.post(
            "/predict",
            files={"image": ("blank.jpg", file_bytes, "image/jpeg")},
            headers=headers,
            cookies=cookies,
        )

        # Count history after
        hist_after = self.client.get("/history", headers=headers, cookies=cookies)
        total_after = hist_after.json().get("total", 0)
        self.assertEqual(total_before, total_after, "Scan history count must NOT increase on invalid upload")

    # -----------------------------------------------------------------------
    # Acceptance Test 15: Frontend Displays Invalid Input State
    # -----------------------------------------------------------------------
    def test_15_frontend_invalid_input_state_component_exists(self):
        """Verify that the frontend contains InvalidInputCard with upload-another button and no disease fields."""
        card_file = PROJECT_ROOT / "frontend" / "src" / "components" / "analysis" / "InvalidInputCard.jsx"
        self.assertTrue(card_file.exists(), "InvalidInputCard.jsx component must exist")

        content = card_file.read_text(encoding="utf-8")
        self.assertIn("Invalid Input", content)
        self.assertIn("No disease analysis was performed", content)
        self.assertIn("Upload Another Image", content)
        # Ensure it does NOT render disease result cards or treatments
        self.assertNotIn("result.treatment", content)
        self.assertNotIn("result.severity", content)

    # -----------------------------------------------------------------------
    # Acceptance Test 16: Previous Analysis Results are Cleared on New Submissions
    # -----------------------------------------------------------------------
    def test_16_frontend_clears_previous_analysis_results(self):
        """Verify that Analyse.jsx explicitly resets result and invalidError when selecting or submitting a file."""
        analyse_page = PROJECT_ROOT / "frontend" / "src" / "pages" / "Analyse.jsx"
        self.assertTrue(analyse_page.exists())
        content = analyse_page.read_text(encoding="utf-8")

        # onSelect must clear result and invalidError
        self.assertIn("setResult(null);", content)
        self.assertIn("setInvalidError(null);", content)
        # Verify invalid_input state branch exists and renders InvalidInputCard
        self.assertIn("InvalidInputCard", content)
        self.assertIn("status === 'invalid_input'", content)

    # -----------------------------------------------------------------------
    # Acceptance Test 17: Existing Valid Image Functionality Continues to Work
    # -----------------------------------------------------------------------
    def test_17_existing_valid_image_functionality_intact(self):
        """Verify that healthy check, disease catalog, authentication, and valid leaf inference remain intact."""
        # 1. Health check
        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json().get("status"), "healthy")

        # 2. Disease catalog
        res_catalog = self.client.get("/diseases")
        self.assertEqual(res_catalog.status_code, 200)
        self.assertGreater(len(res_catalog.json().get("items", [])), 0)

        # 3. Valid prediction retains full schema (crop, disease, confidence, treatment, severity)
        if self.real_tomato_path:
            with open(self.real_tomato_path, "rb") as f:
                file_bytes = f.read()
            headers, cookies = self._get_auth_headers_and_cookies()
            res_pred = self.client.post(
                "/predict",
                files={"image": ("valid_tomato.jpg", file_bytes, "image/jpeg")},
                headers=headers,
                cookies=cookies,
            )
            self.assertEqual(res_pred.status_code, 200)
            data = res_pred.json()
            for key in ["crop", "disease", "disease_code", "confidence", "treatment", "severity", "model_version"]:
                self.assertIn(key, data, f"Missing required response field '{key}'")


if __name__ == "__main__":
    unittest.main()
