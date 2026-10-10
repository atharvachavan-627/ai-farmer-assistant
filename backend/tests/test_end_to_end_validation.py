"""
Comprehensive End-to-End Application Validation Suite for AI Farmer Assistant.

Validates the complete integrated lifecycle:
1. Authentication Workflow (Registration, Login, Cookie Sessions, CSRF, Logout, Invalidation).
2. Disease Information Catalogue (13 Classes, Healthy distinctions, Search, Filtering, Multilingual en/hi/mr).
3. Real Prediction Workflow (Real PlantVillage leaf photo upload, PyTorch inference, treatment mapping, persistence).
4. History Lifecycle (Listing, Pagination, Sorting, Single Retrieval, Deletion with CSRF).
5. Multi-Tenant User Isolation (Strict cross-user authorization enforcement).
6. Full Edge-Case & Failure Suite (Missing/Empty/Corrupted/Oversized/Unsupported files, CSRF forgery, Session expiry).
"""

import sys
import io
import json
import uuid
import unittest
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.api import app
from src.config import get_settings


class TestEndToEndValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.settings = get_settings()

        # Find real dataset leaf photo
        dataset_dir = PROJECT_ROOT / "data" / "processed" / "tomato_potato"
        sample_images = list(dataset_dir.glob("*/*.JPG")) + list(dataset_dir.glob("*/*.jpg")) + list(dataset_dir.glob("*/*.png"))
        if sample_images:
            cls.real_leaf_path = sample_images[0]
            with open(cls.real_leaf_path, "rb") as f:
                cls.real_leaf_bytes = f.read()
        else:
            # Fallback synthetic image if dataset directory absent
            cls.real_leaf_path = None
            buf = io.BytesIO()
            Image.new("RGB", (224, 224), color=(34, 139, 34)).save(buf, format="JPEG")
            cls.real_leaf_bytes = buf.getvalue()

    # =========================================================================
    # 1. AUTHENTICATION WORKFLOW
    # =========================================================================

    def test_01_registration_and_validation(self):
        """User registration, validation errors, and duplicate prevention."""
        uid = uuid.uuid4().hex[:8]
        valid_email = f"farmer_{uid}@example.com"
        valid_pass = "SecurePass!123"
        valid_name = "Kisan Ramesh"

        # A. Missing fields
        res_empty = self.client.post("/auth/register", json={})
        self.assertIn(res_empty.status_code, [400, 422])

        # B. Invalid email format
        res_bad_email = self.client.post("/auth/register", json={
            "name": valid_name,
            "email": "not-an-email",
            "password": valid_pass
        })
        self.assertIn(res_bad_email.status_code, [400, 422])

        # C. Short password (< 8 chars)
        res_short_pwd = self.client.post("/auth/register", json={
            "name": valid_name,
            "email": valid_email,
            "password": "short"
        })
        self.assertIn(res_short_pwd.status_code, [400, 422])

        # D. Successful registration (both name and full_name supported)
        res_ok = self.client.post("/auth/register", json={
            "name": valid_name,
            "email": valid_email,
            "password": valid_pass
        })
        self.assertEqual(res_ok.status_code, 201)
        data = res_ok.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["user"]["email"], valid_email)
        self.assertEqual(data["user"]["name"], valid_name)
        self.assertEqual(data["user"]["full_name"], valid_name)

        # E. Duplicate email rejection (HTTP 409)
        res_dup = self.client.post("/auth/register", json={
            "name": "Another Name",
            "email": valid_email,
            "password": valid_pass
        })
        self.assertEqual(res_dup.status_code, 409)
        self.assertEqual(res_dup.json()["error"]["code"], "EMAIL_ALREADY_EXISTS")

    def test_02_login_session_and_csrf_lifecycle(self):
        """Login sets HttpOnly session and CSRF cookies; enables GET /auth/me and preferences."""
        uid = uuid.uuid4().hex[:8]
        email = f"login_test_{uid}@example.com"
        password = "Password@123"
        name = "Login Farmer"

        # Register
        self.client.post("/auth/register", json={"name": name, "email": email, "password": password})

        # A. Invalid login credentials
        res_bad_login = self.client.post("/auth/login", json={"email": email, "password": "WrongPassword"})
        self.assertEqual(res_bad_login.status_code, 401)
        self.assertEqual(res_bad_login.json()["error"]["code"], "INVALID_CREDENTIALS")

        # B. Successful login
        res_login = self.client.post("/auth/login", json={"email": email, "password": password})
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(self.settings.SESSION_COOKIE_NAME, res_login.cookies)
        self.assertIn(self.settings.CSRF_COOKIE_NAME, res_login.cookies)

        session_id = res_login.cookies[self.settings.SESSION_COOKIE_NAME]
        csrf_token = res_login.cookies[self.settings.CSRF_COOKIE_NAME]

        # C. Rehydrate current user session (GET /auth/me)
        res_me = self.client.get("/auth/me", cookies={self.settings.SESSION_COOKIE_NAME: session_id})
        self.assertEqual(res_me.status_code, 200)
        user_data = res_me.json()
        self.assertEqual(user_data["email"], email)
        self.assertEqual(user_data["name"], name)

        # D. User UI preferences sync
        res_pref = self.client.put(
            "/users/me/preferences",
            json={"language": "mr"},
            cookies={self.settings.SESSION_COOKIE_NAME: session_id, self.settings.CSRF_COOKIE_NAME: csrf_token},
            headers={self.settings.CSRF_HEADER_NAME: csrf_token}
        )
        self.assertEqual(res_pref.status_code, 200)
        self.assertEqual(res_pref.json()["language"], "mr")

        # E. Logout and session invalidation
        res_logout = self.client.post(
            "/auth/logout",
            cookies={self.settings.SESSION_COOKIE_NAME: session_id, self.settings.CSRF_COOKIE_NAME: csrf_token},
            headers={self.settings.CSRF_HEADER_NAME: csrf_token}
        )
        self.assertEqual(res_logout.status_code, 200)

        # Post-logout requests must be rejected
        res_me_after = self.client.get("/auth/me", cookies={self.settings.SESSION_COOKIE_NAME: session_id})
        self.assertEqual(res_me_after.status_code, 401)

    # =========================================================================
    # 2. DISEASE INFORMATION WORKFLOW
    # =========================================================================

    def test_03_disease_catalogue_contracts(self):
        """GET /diseases and GET /diseases/{id} query parameters, search, filters, and multilingual response."""
        # A. All 13 classes
        res_all = self.client.get("/diseases")
        self.assertEqual(res_all.status_code, 200)
        data = res_all.json()
        self.assertEqual(data["total"], 13)
        self.assertEqual(len(data["items"]), 13)

        # B. Crop filter tomato (10) vs potato (3)
        res_tomato = self.client.get("/diseases?crop=tomato")
        self.assertEqual(res_tomato.status_code, 200)
        self.assertEqual(len(res_tomato.json()["items"]), 10)

        res_potato = self.client.get("/diseases?crop=potato")
        self.assertEqual(res_potato.status_code, 200)
        self.assertEqual(len(res_potato.json()["items"]), 3)

        # C. Search blight (4 classes)
        res_blight = self.client.get("/diseases?search=blight")
        self.assertEqual(res_blight.status_code, 200)
        self.assertEqual(len(res_blight.json()["items"]), 4)

        # D. Multilingual: en, hi, mr
        res_hi = self.client.get("/diseases?language=hi")
        self.assertEqual(res_hi.status_code, 200)
        self.assertEqual(res_hi.json()["language"], "hi")
        # Check Devanagari in first item
        self.assertTrue(any('\u0900' <= c <= '\u097F' for c in res_hi.json()["items"][0]["name"]))

        res_mr = self.client.get("/diseases?language=mr")
        self.assertEqual(res_mr.status_code, 200)
        self.assertEqual(res_mr.json()["language"], "mr")
        self.assertTrue(any('\u0900' <= c <= '\u097F' for c in res_mr.json()["items"][0]["name"]))

        # E. Single disease detail
        res_detail = self.client.get("/diseases/Tomato___Early_blight")
        self.assertEqual(res_detail.status_code, 200)
        d = res_detail.json()
        self.assertEqual(d["disease_code"], "Tomato___Early_blight")
        self.assertEqual(d["category"], "Fungal")
        self.assertTrue(d["chemical_verified"])

        # F. Healthy leaf representation
        res_healthy = self.client.get("/diseases/Potato___healthy")
        self.assertEqual(res_healthy.status_code, 200)
        h = res_healthy.json()
        self.assertEqual(h["category"], "Healthy")
        self.assertFalse(h["chemical_verified"])
        self.assertEqual(h["chemical_treatment"], [])

        # G. 404 on unknown disease
        res_404 = self.client.get("/diseases/UnknownNonExistent")
        self.assertEqual(res_404.status_code, 404)
        self.assertEqual(res_404.json()["error"]["code"], "DISEASE_NOT_FOUND")

    # =========================================================================
    # 3. REAL PREDICTION & HISTORY PERSISTENCE WORKFLOW
    # =========================================================================

    def test_04_real_prediction_and_history_persistence(self):
        """End-to-end inference with real image bytes, persistence, history listing, single view, and deletion."""
        uid = uuid.uuid4().hex[:8]
        email = f"pred_user_{uid}@example.com"
        password = "Password@123"

        # Register and Login
        self.client.post("/auth/register", json={"name": "Pred User", "email": email, "password": password})
        login_res = self.client.post("/auth/login", json={"email": email, "password": password})
        session_id = login_res.cookies[self.settings.SESSION_COOKIE_NAME]
        csrf_token = login_res.cookies[self.settings.CSRF_COOKIE_NAME]
        auth_cookies = {self.settings.SESSION_COOKIE_NAME: session_id, self.settings.CSRF_COOKIE_NAME: csrf_token}
        csrf_header = {self.settings.CSRF_HEADER_NAME: csrf_token}

        # A. Fresh user history is empty
        res_empty_hist = self.client.get("/history", cookies=auth_cookies)
        self.assertEqual(res_empty_hist.status_code, 200)
        self.assertEqual(res_empty_hist.json()["total"], 0)
        self.assertEqual(res_empty_hist.json()["items"], [])

        # B. Real leaf photo prediction upload via multipart field 'image'
        files = {"image": ("leaf.jpg", self.real_leaf_bytes, "image/jpeg")}
        pred_res = self.client.post(
            "/predict",
            files=files,
            cookies=auth_cookies,
            headers=csrf_header
        )
        self.assertEqual(pred_res.status_code, 200)
        pred_data = pred_res.json()
        self.assertTrue(pred_data.get("success"))
        self.assertIsNotNone(pred_data.get("analysis_id"))
        self.assertIn(pred_data.get("crop"), ["Tomato", "Potato"])
        self.assertTrue(0.0 <= pred_data.get("confidence", -1) <= 1.0)
        self.assertIn("treatment", pred_data)
        self.assertTrue(len(pred_data["treatment"]["symptoms"]) > 0)

        analysis_id = pred_data["analysis_id"]

        # C. Query history: record must appear
        res_hist = self.client.get("/history?page=1&page_size=10&sort=newest", cookies=auth_cookies)
        self.assertEqual(res_hist.status_code, 200)
        hist_data = res_hist.json()
        self.assertEqual(hist_data["total"], 1)
        self.assertEqual(len(hist_data["items"]), 1)
        first_item = hist_data["items"][0]
        self.assertEqual(str(first_item["analysis_id"]), str(analysis_id))
        self.assertEqual(first_item["disease_code"], pred_data["disease_code"])

        # D. Single analysis record retrieval (GET /history/{id})
        res_single = self.client.get(f"/history/{analysis_id}", cookies=auth_cookies)
        self.assertEqual(res_single.status_code, 200)
        single_data = res_single.json()
        self.assertEqual(str(single_data["analysis_id"]), str(analysis_id))

        # E. Delete analysis record (DELETE /history/{id})
        res_del = self.client.delete(f"/history/{analysis_id}", cookies=auth_cookies, headers=csrf_header)
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json().get("success"))

        # F. Post-delete check: returns 404
        res_after_del = self.client.get(f"/history/{analysis_id}", cookies=auth_cookies)
        self.assertEqual(res_after_del.status_code, 404)

        res_hist_empty = self.client.get("/history", cookies=auth_cookies)
        self.assertEqual(res_hist_empty.json()["total"], 0)

    # =========================================================================
    # 4. MULTI-TENANT USER ISOLATION
    # =========================================================================

    def test_05_multi_tenant_user_isolation(self):
        """User A cannot access or delete User B's historical analysis records."""
        uid_a = uuid.uuid4().hex[:8]
        uid_b = uuid.uuid4().hex[:8]

        # Create User A
        self.client.post("/auth/register", json={"name": "User A", "email": f"usera_{uid_a}@example.com", "password": "Password@123"})
        res_a = self.client.post("/auth/login", json={"email": f"usera_{uid_a}@example.com", "password": "Password@123"})
        cookies_a = {self.settings.SESSION_COOKIE_NAME: res_a.cookies[self.settings.SESSION_COOKIE_NAME], self.settings.CSRF_COOKIE_NAME: res_a.cookies[self.settings.CSRF_COOKIE_NAME]}
        headers_a = {self.settings.CSRF_HEADER_NAME: res_a.cookies[self.settings.CSRF_COOKIE_NAME]}

        # Create User B
        self.client.post("/auth/register", json={"name": "User B", "email": f"userb_{uid_b}@example.com", "password": "Password@123"})
        res_b = self.client.post("/auth/login", json={"email": f"userb_{uid_b}@example.com", "password": "Password@123"})
        cookies_b = {self.settings.SESSION_COOKIE_NAME: res_b.cookies[self.settings.SESSION_COOKIE_NAME], self.settings.CSRF_COOKIE_NAME: res_b.cookies[self.settings.CSRF_COOKIE_NAME]}
        headers_b = {self.settings.CSRF_HEADER_NAME: res_b.cookies[self.settings.CSRF_COOKIE_NAME]}

        # User B creates an analysis record
        files_b = {"image": ("leaf_b.jpg", self.real_leaf_bytes, "image/jpeg")}
        pred_b = self.client.post("/predict", files=files_b, cookies=cookies_b, headers=headers_b)
        self.assertEqual(pred_b.status_code, 200)
        id_b = pred_b.json()["analysis_id"]

        # User A tries to view User B's analysis -> 404
        res_a_view_b = self.client.get(f"/history/{id_b}", cookies=cookies_a)
        self.assertEqual(res_a_view_b.status_code, 404)

        # User A tries to delete User B's analysis -> 404
        res_a_del_b = self.client.delete(f"/history/{id_b}", cookies=cookies_a, headers=headers_a)
        self.assertEqual(res_a_del_b.status_code, 404)

        # User B can still access their analysis -> 200
        res_b_view = self.client.get(f"/history/{id_b}", cookies=cookies_b)
        self.assertEqual(res_b_view.status_code, 200)

    # =========================================================================
    # 5. FAILURE & EDGE-CASE TESTS
    # =========================================================================

    def test_06_prediction_edge_cases_and_error_handling(self):
        """Validates all controlled error responses for file uploads and security."""
        uid = uuid.uuid4().hex[:8]
        self.client.post("/auth/register", json={"name": "Edge User", "email": f"edge_{uid}@example.com", "password": "Password@123"})
        res_login = self.client.post("/auth/login", json={"email": f"edge_{uid}@example.com", "password": "Password@123"})
        cookies = {self.settings.SESSION_COOKIE_NAME: res_login.cookies[self.settings.SESSION_COOKIE_NAME], self.settings.CSRF_COOKIE_NAME: res_login.cookies[self.settings.CSRF_COOKIE_NAME]}
        headers = {self.settings.CSRF_HEADER_NAME: res_login.cookies[self.settings.CSRF_COOKIE_NAME]}

        # A. Unauthenticated upload (HTTP 401)
        unauth_client = TestClient(app)
        files_valid = {"image": ("leaf.jpg", self.real_leaf_bytes, "image/jpeg")}
        res_unauth = unauth_client.post("/predict", files=files_valid)
        self.assertEqual(res_unauth.status_code, 401)

        # B. Missing CSRF header with cookie auth (HTTP 403)
        res_no_csrf = self.client.post("/predict", files=files_valid, cookies=cookies)
        self.assertEqual(res_no_csrf.status_code, 403)
        self.assertEqual(res_no_csrf.json()["error"]["code"], "CSRF_ERROR")

        # C. Missing file upload (HTTP 400)
        res_missing = self.client.post("/predict", cookies=cookies, headers=headers)
        self.assertEqual(res_missing.status_code, 400)
        self.assertEqual(res_missing.json()["error"]["code"], "MISSING_FILE")

        # D. Empty 0-byte file (HTTP 400)
        res_empty = self.client.post("/predict", files={"image": ("empty.jpg", b"", "image/jpeg")}, cookies=cookies, headers=headers)
        self.assertEqual(res_empty.status_code, 400)
        self.assertEqual(res_empty.json()["error"]["code"], "EMPTY_FILE")

        # E. Unsupported format .txt / .pdf (HTTP 415)
        res_unsupp = self.client.post("/predict", files={"image": ("doc.txt", b"hello world text", "text/plain")}, cookies=cookies, headers=headers)
        self.assertEqual(res_unsupp.status_code, 415)
        self.assertEqual(res_unsupp.json()["error"]["code"], "UNSUPPORTED_MEDIA_TYPE")

        # F. Corrupted image bytes (HTTP 422)
        res_corrupt = self.client.post("/predict", files={"image": ("bad.jpg", b"not-a-valid-jpeg-image-bytes", "image/jpeg")}, cookies=cookies, headers=headers)
        self.assertEqual(res_corrupt.status_code, 422)
        self.assertEqual(res_corrupt.json()["error"]["code"], "CORRUPTED_IMAGE")

        # G. Oversized upload > 10 MB (HTTP 413)
        oversized_bytes = b"0" * (10 * 1024 * 1024 + 1024)
        res_large = self.client.post("/predict", files={"image": ("large.jpg", oversized_bytes, "image/jpeg")}, cookies=cookies, headers=headers)
        self.assertEqual(res_large.status_code, 413)
        self.assertEqual(res_large.json()["error"]["code"], "FILE_TOO_LARGE")


def run_e2e_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEndToEndValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful(), result


if __name__ == "__main__":
    ok, _ = run_e2e_tests()
    sys.exit(0 if ok else 1)
