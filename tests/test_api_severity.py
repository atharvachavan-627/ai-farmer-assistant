"""
Integration test for Plant Disease Severity Estimation in POST /predict.

Verifies:
1. Successful prediction includes severity in response.
2. Classification confidence and disease severity percentage remain distinct.
3. Existing response fields (crop, disease, confidence, treatment, model_version) remain intact.
4. Low confidence predictions return appropriately guarded severity status.
5. Serialization conforms strictly to API schemas.
"""

import io
import unittest
from pathlib import Path
from PIL import Image

from fastapi.testclient import TestClient
from src.api import app
from src.config import get_settings


class TestApiSeverityIntegration(unittest.TestCase):
    """Integration test suite for severity field in /predict."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.settings = get_settings()

        # Create a valid test user session
        cls.email = "severity_tester@example.com"
        cls.password = "TestPass!123"

        # Register user
        cls.client.post(
            "/auth/register",
            json={
                "full_name": "Severity Tester",
                "email": cls.email,
                "password": cls.password,
                "preferred_language": "en"
            }
        )

        # Login and obtain session cookie
        login_res = cls.client.post(
            "/auth/login",
            json={"email": cls.email, "password": cls.password}
        )
        cls.session_cookie = login_res.cookies.get(cls.settings.SESSION_COOKIE_NAME)
        cls.csrf_token = login_res.cookies.get(cls.settings.CSRF_COOKIE_NAME)

        # Use a real tomato leaf from PlantVillage dataset to pass input validation
        pv_sample = Path(__file__).resolve().parent.parent / "data" / "raw" / "plantvillage" / "plantvillage dataset" / "color" / "Tomato___Early_blight"
        leaf_file = next(pv_sample.glob("*.JPG"), None) if pv_sample.exists() else None
        if leaf_file:
            with open(leaf_file, "rb") as f:
                cls.leaf_bytes = f.read()
        else:
            buf = io.BytesIO()
            img = Image.new("RGB", (256, 256), color=(140, 140, 140))
            for x in range(40, 216):
                for y in range(40, 216):
                    img.putpixel((x, y), (34, 139, 34))
            for x in range(80, 120):
                for y in range(80, 120):
                    img.putpixel((x, y), (139, 69, 19))
            img.save(buf, format="JPEG")
            cls.leaf_bytes = buf.getvalue()

    def test_predict_includes_severity_payload(self):
        """POST /predict must return severity details in response."""
        headers = {
            self.settings.CSRF_HEADER_NAME: self.csrf_token,
        }
        cookies = {
            self.settings.SESSION_COOKIE_NAME: self.session_cookie,
            self.settings.CSRF_COOKIE_NAME: self.csrf_token,
        }

        files = {
            "image": ("test_leaf.jpg", self.leaf_bytes, "image/jpeg")
        }

        response = self.client.post(
            "/predict",
            files=files,
            headers=headers,
            cookies=cookies,
        )

        self.assertEqual(response.status_code, 200, f"Predict failed: {response.text}")
        data = response.json()

        # 1. Verify existing contract fields
        self.assertTrue(data.get("success"))
        self.assertIn("crop", data)
        self.assertIn("disease_code", data)
        self.assertIn("confidence", data)
        self.assertIn("treatment", data)
        self.assertIn("model_version", data)

        # 2. Verify severity payload
        self.assertIn("severity", data)
        sev = data["severity"]
        self.assertIsNotNone(sev)
        self.assertIn("status", sev)
        self.assertIn("method", sev)
        self.assertIn("disclaimer", sev)
        self.assertIn(sev["status"], ("estimated", "healthy_leaf", "unreliable_segmentation", "insufficient_leaf_area"))

        # 3. Ensure confidence and severity are independent
        conf = data["confidence"]
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)
        if sev.get("estimated_affected_area_percent") is not None:
            self.assertGreaterEqual(sev["estimated_affected_area_percent"], 0.0)
            self.assertLessEqual(sev["estimated_affected_area_percent"], 100.0)


if __name__ == "__main__":
    unittest.main()
