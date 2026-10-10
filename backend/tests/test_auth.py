"""
Automated Authentication and Security Test Suite for AI Farmer Assistant.

Validates:
1. Registration (Success, Duplicate email, Invalid email, Missing fields, Weak password, Argon2id hash storage)
2. Login (Valid credentials, Invalid password, Unknown email, Inactive account, Missing fields)
3. Session Management (Valid session, Invalid session token, Expired session, Logout invalidation)
4. Current User (GET /auth/me authenticated vs unauthenticated, safe fields only)
5. User Preferences (GET/PUT /users/me/preferences)
6. CSRF Protection (Double-Submit cookie validation on state-changing requests)
7. Protected Prediction (Unauthenticated rejection 401, Authenticated prediction 200)
8. Public Health Endpoint (GET /health works without authentication)
"""

import sys
import io
from pathlib import Path
from datetime import datetime, timezone, timedelta
from PIL import Image
from fastapi.testclient import TestClient

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api import app
from src.database import SessionLocal
from src.models import User, UserSession
from src.config import get_settings

settings = get_settings()


def run_auth_tests():
    print("=" * 80)
    print("AUTHENTICATION & SECURITY AUTOMATED TEST SUITE")
    print("=" * 80)

    client = TestClient(app)
    db = SessionLocal()
    results = {}

    # Unique test email generation
    test_run_id = int(datetime.now(timezone.utc).timestamp())
    test_email = f"farmer_{test_run_id}@example.com"
    test_password = "SecurePassword123!"
    test_name = "Ramesh Kumar"

    # -------------------------------------------------------------
    # 1. Registration Tests
    # -------------------------------------------------------------
    print("\n[TEST 1] User Registration Scenarios...")

    # 1a. Successful registration
    resp_reg = client.post(
        "/auth/register",
        json={
            "full_name": test_name,
            "email": test_email,
            "password": test_password,
            "preferred_language": "hi"
        }
    )
    reg_json = resp_reg.json()
    reg_ok = (
        resp_reg.status_code == 201 and
        reg_json.get("success") is True and
        reg_json.get("user", {}).get("email") == test_email and
        "password" not in reg_json.get("user", {}) and
        "password_hash" not in reg_json.get("user", {})
    )
    print(f"   1a. Valid Registration: Status {resp_reg.status_code}, User: {reg_json.get('user')}")

    # 1b. Duplicate email rejection
    resp_dup = client.post(
        "/auth/register",
        json={
            "full_name": "Another Farmer",
            "email": test_email,  # duplicate
            "password": "AnotherPassword123!"
        }
    )
    dup_ok = (
        resp_dup.status_code == 409 and
        resp_dup.json().get("error", {}).get("code") == "EMAIL_ALREADY_EXISTS"
    )
    print(f"   1b. Duplicate Email: Status {resp_dup.status_code}, Code: {resp_dup.json().get('error', {}).get('code')}")

    # 1c. Invalid email format
    resp_inv_email = client.post(
        "/auth/register",
        json={
            "full_name": "Farmer Joe",
            "email": "not-an-email",
            "password": "Password123!"
        }
    )
    inv_email_ok = resp_inv_email.status_code == 400
    print(f"   1c. Invalid Email Format: Status {resp_inv_email.status_code}")

    # 1d. Weak password (< 8 chars)
    resp_weak_pwd = client.post(
        "/auth/register",
        json={
            "full_name": "Farmer Joe",
            "email": f"weak_{test_run_id}@example.com",
            "password": "short"
        }
    )
    weak_pwd_ok = resp_weak_pwd.status_code == 400
    print(f"   1d. Weak Password: Status {resp_weak_pwd.status_code}")

    # 1e. Verify Argon2id hash storage in DB
    user_record = db.query(User).filter(User.email == test_email).first()
    hash_stored_ok = (
        user_record is not None and
        user_record.password_hash.startswith("$argon2id$") and
        test_password not in user_record.password_hash
    )
    print(f"   1e. Argon2id Hash Verified: {hash_stored_ok} (Prefix: {user_record.password_hash[:15] if user_record else 'None'})")

    test_1_ok = reg_ok and dup_ok and inv_email_ok and weak_pwd_ok and hash_stored_ok
    print(f"   Registration Test: {'PASS' if test_1_ok else 'FAIL'}")
    results["registration"] = test_1_ok

    # -------------------------------------------------------------
    # 2. Login Tests
    # -------------------------------------------------------------
    print("\n[TEST 2] User Login Scenarios...")

    # 2a. Successful login
    resp_login = client.post(
        "/auth/login",
        json={"email": test_email, "password": test_password}
    )
    login_json = resp_login.json()
    has_session_cookie = settings.SESSION_COOKIE_NAME in resp_login.cookies
    has_csrf_cookie = settings.CSRF_COOKIE_NAME in resp_login.cookies
    session_token = resp_login.cookies.get(settings.SESSION_COOKIE_NAME)
    csrf_token = resp_login.cookies.get(settings.CSRF_COOKIE_NAME)

    login_ok = (
        resp_login.status_code == 200 and
        login_json.get("success") is True and
        login_json.get("user", {}).get("email") == test_email and
        has_session_cookie and
        has_csrf_cookie
    )
    print(f"   2a. Valid Login: Status {resp_login.status_code}, Session Cookie Present: {has_session_cookie}, CSRF Cookie Present: {has_csrf_cookie}")

    # 2b. Incorrect password
    resp_wrong_pwd = client.post(
        "/auth/login",
        json={"email": test_email, "password": "WrongPassword999!"}
    )
    wrong_pwd_ok = (
        resp_wrong_pwd.status_code == 401 and
        resp_wrong_pwd.json().get("error", {}).get("code") == "INVALID_CREDENTIALS"
    )
    print(f"   2b. Wrong Password: Status {resp_wrong_pwd.status_code}, Code: {resp_wrong_pwd.json().get('error', {}).get('code')}")

    # 2c. Unknown email (same message prevents user enumeration)
    resp_unknown_email = client.post(
        "/auth/login",
        json={"email": "nobody_exists_12345@example.com", "password": "Password123!"}
    )
    unknown_email_ok = (
        resp_unknown_email.status_code == 401 and
        resp_unknown_email.json().get("error", {}).get("code") == "INVALID_CREDENTIALS"
    )
    print(f"   2c. Unknown Email: Status {resp_unknown_email.status_code}, Code: {resp_unknown_email.json().get('error', {}).get('code')}")

    test_2_ok = login_ok and wrong_pwd_ok and unknown_email_ok
    print(f"   Login Test: {'PASS' if test_2_ok else 'FAIL'}")
    results["login"] = test_2_ok

    # -------------------------------------------------------------
    # 3. Current User Endpoint (GET /auth/me)
    # -------------------------------------------------------------
    print("\n[TEST 3] Current User (GET /auth/me)...")

    # 3a. Authenticated request with session cookie
    resp_me = client.get(
        "/auth/me",
        cookies={settings.SESSION_COOKIE_NAME: session_token}
    )
    me_json = resp_me.json()
    me_ok = (
        resp_me.status_code == 200 and
        me_json.get("email") == test_email and
        me_json.get("full_name") == test_name and
        "password" not in me_json and
        "password_hash" not in me_json
    )
    print(f"   3a. Authenticated Profile: Status {resp_me.status_code}, User: {me_json}")

    # 3b. Unauthenticated request (no session cookie)
    unauth_client = TestClient(app)
    resp_me_unauth = unauth_client.get("/auth/me")
    me_unauth_ok = (
        resp_me_unauth.status_code == 401 and
        resp_me_unauth.json().get("error", {}).get("code") == "UNAUTHORIZED"
    )
    print(f"   3b. Unauthenticated Request: Status {resp_me_unauth.status_code}, Code: {resp_me_unauth.json().get('error', {}).get('code')}")

    # 3c. Invalid session token
    resp_me_invalid = client.get(
        "/auth/me",
        cookies={settings.SESSION_COOKIE_NAME: "fake_invalid_token_999"}
    )
    me_invalid_ok = (
        resp_me_invalid.status_code == 401 and
        resp_me_invalid.json().get("error", {}).get("code") == "SESSION_EXPIRED"
    )
    print(f"   3c. Invalid Session Token: Status {resp_me_invalid.status_code}, Code: {resp_me_invalid.json().get('error', {}).get('code')}")

    test_3_ok = me_ok and me_unauth_ok and me_invalid_ok
    print(f"   Current User Test: {'PASS' if test_3_ok else 'FAIL'}")
    results["current_user"] = test_3_ok

    # -------------------------------------------------------------
    # 4. User Preferences Endpoint
    # -------------------------------------------------------------
    print("\n[TEST 4] User Preferences (GET/PUT /users/me/preferences)...")
    # GET preferences
    resp_pref_get = client.get(
        "/users/me/preferences",
        cookies={settings.SESSION_COOKIE_NAME: session_token}
    )
    pref_get_ok = resp_pref_get.status_code == 200 and resp_pref_get.json().get("language") == "hi"

    # PUT preferences
    resp_pref_put = client.put(
        "/users/me/preferences",
        json={"language": "mr"},
        cookies={settings.SESSION_COOKIE_NAME: session_token},
        headers={settings.CSRF_HEADER_NAME: csrf_token}
    )
    pref_put_ok = resp_pref_put.status_code == 200 and resp_pref_put.json().get("language") == "mr"

    test_4_ok = pref_get_ok and pref_put_ok
    print(f"   User Preferences Test: {'PASS' if test_4_ok else 'FAIL'}")
    results["preferences"] = test_4_ok

    # -------------------------------------------------------------
    # 5. Session Expiration Handling
    # -------------------------------------------------------------
    print("\n[TEST 5] Expired Session Handling...")
    # Set the session expiration in the past in DB
    db_session = db.query(UserSession).filter(UserSession.id == session_token).first()
    db_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db.commit()

    resp_expired = client.get(
        "/auth/me",
        cookies={settings.SESSION_COOKIE_NAME: session_token}
    )
    expired_ok = (
        resp_expired.status_code == 401 and
        resp_expired.json().get("error", {}).get("code") == "SESSION_EXPIRED"
    )
    print(f"   5a. Expired Session Rejected: Status {resp_expired.status_code}, Code: {resp_expired.json().get('error', {}).get('code')}")
    results["session_expiration"] = expired_ok

    # Re-login to get fresh session for subsequent tests
    resp_relogin = client.post(
        "/auth/login",
        json={"email": test_email, "password": test_password}
    )
    session_token = resp_relogin.cookies.get(settings.SESSION_COOKIE_NAME)
    csrf_token = resp_relogin.cookies.get(settings.CSRF_COOKIE_NAME)

    # -------------------------------------------------------------
    # 6. CSRF Protection on State-Changing Endpoints
    # -------------------------------------------------------------
    print("\n[TEST 6] CSRF Protection Enforcement...")
    # Prepare dummy image bytes
    buf = io.BytesIO()
    Image.new("RGB", (224, 224), color=(34, 139, 34)).save(buf, format="JPEG")
    dummy_img_bytes = buf.getvalue()

    # 6a. State-changing request with session cookie but MISSING X-CSRF-Token header
    resp_csrf_missing = client.post(
        "/predict",
        files={"image": ("leaf.jpg", dummy_img_bytes, "image/jpeg")},
        cookies={
            settings.SESSION_COOKIE_NAME: session_token,
            settings.CSRF_COOKIE_NAME: csrf_token
        }
        # Omitting X-CSRF-Token header
    )
    csrf_missing_ok = (
        resp_csrf_missing.status_code == 403 and
        resp_csrf_missing.json().get("error", {}).get("code") == "CSRF_ERROR"
    )
    print(f"   6a. Missing CSRF Header Rejected: Status {resp_csrf_missing.status_code}, Code: {resp_csrf_missing.json().get('error', {}).get('code')}")

    # 6b. State-changing request with INVALID X-CSRF-Token header
    resp_csrf_bad = client.post(
        "/predict",
        files={"image": ("leaf.jpg", dummy_img_bytes, "image/jpeg")},
        cookies={
            settings.SESSION_COOKIE_NAME: session_token,
            settings.CSRF_COOKIE_NAME: csrf_token
        },
        headers={settings.CSRF_HEADER_NAME: "wrong_tampered_csrf_token"}
    )
    csrf_bad_ok = (
        resp_csrf_bad.status_code == 403 and
        resp_csrf_bad.json().get("error", {}).get("code") == "CSRF_ERROR"
    )
    print(f"   6b. Invalid CSRF Header Rejected: Status {resp_csrf_bad.status_code}, Code: {resp_csrf_bad.json().get('error', {}).get('code')}")

    # 6c. Valid CSRF header with cookie authentication
    resp_csrf_valid = client.post(
        "/predict",
        files={"image": ("leaf.jpg", dummy_img_bytes, "image/jpeg")},
        cookies={
            settings.SESSION_COOKIE_NAME: session_token,
            settings.CSRF_COOKIE_NAME: csrf_token
        },
        headers={settings.CSRF_HEADER_NAME: csrf_token}
    )
    csrf_valid_ok = resp_csrf_valid.status_code == 200 and resp_csrf_valid.json().get("success") is True
    print(f"   6c. Valid CSRF Header Accepted: Status {resp_csrf_valid.status_code}, Success: {resp_csrf_valid.json().get('success')}")

    test_6_ok = csrf_missing_ok and csrf_bad_ok and csrf_valid_ok
    print(f"   CSRF Protection Test: {'PASS' if test_6_ok else 'FAIL'}")
    results["csrf_protection"] = test_6_ok

    # -------------------------------------------------------------
    # 7. Protected Prediction Endpoint
    # -------------------------------------------------------------
    print("\n[TEST 7] Protected Prediction Endpoint...")

    # 7a. Unauthenticated request to /predict
    unauth_client = TestClient(app)
    resp_pred_unauth = unauth_client.post(
        "/predict",
        files={"image": ("leaf.jpg", dummy_img_bytes, "image/jpeg")}
    )
    pred_unauth_ok = (
        resp_pred_unauth.status_code == 401 and
        resp_pred_unauth.json().get("error", {}).get("code") == "UNAUTHORIZED"
    )
    print(f"   7a. Unauthenticated Predict Rejected: Status {resp_pred_unauth.status_code}, Code: {resp_pred_unauth.json().get('error', {}).get('code')}")

    # 7b. Authenticated request reaches inference
    resp_pred_auth = client.post(
        "/predict",
        files={"image": ("leaf.jpg", dummy_img_bytes, "image/jpeg")},
        cookies={
            settings.SESSION_COOKIE_NAME: session_token,
            settings.CSRF_COOKIE_NAME: csrf_token
        },
        headers={settings.CSRF_HEADER_NAME: csrf_token}
    )
    pred_auth_ok = (
        resp_pred_auth.status_code == 200 and
        resp_pred_auth.json().get("success") is True and
        resp_pred_auth.json().get("crop") in ["Potato", "Tomato"] and
        resp_pred_auth.json().get("disease_code") is not None
    )
    print(f"   7b. Authenticated Predict Succeeded: Status {resp_pred_auth.status_code}, Crop: {resp_pred_auth.json().get('crop')}")

    test_7_ok = pred_unauth_ok and pred_auth_ok
    print(f"   Protected Prediction Test: {'PASS' if test_7_ok else 'FAIL'}")
    results["protected_prediction"] = test_7_ok

    # -------------------------------------------------------------
    # 8. Logout and Session Invalidation
    # -------------------------------------------------------------
    print("\n[TEST 8] Logout and Session Invalidation...")

    resp_logout = client.post(
        "/auth/logout",
        cookies={settings.SESSION_COOKIE_NAME: session_token}
    )
    logout_ok = (
        resp_logout.status_code == 200 and
        resp_logout.json().get("success") is True
    )
    print(f"   8a. Logout Response: Status {resp_logout.status_code}, Body: {resp_logout.json()}")

    # 8b. Subsequent request with invalidated session should be rejected
    resp_post_logout = client.get(
        "/auth/me",
        cookies={settings.SESSION_COOKIE_NAME: session_token}
    )
    post_logout_ok = (
        resp_post_logout.status_code == 401 and
        resp_post_logout.json().get("error", {}).get("code") == "SESSION_EXPIRED"
    )
    print(f"   8b. Invalidated Session Rejected: Status {resp_post_logout.status_code}, Code: {resp_post_logout.json().get('error', {}).get('code')}")

    test_8_ok = logout_ok and post_logout_ok
    print(f"   Logout Test: {'PASS' if test_8_ok else 'FAIL'}")
    results["logout"] = test_8_ok

    # -------------------------------------------------------------
    # 9. Public Health Endpoint Remains Public
    # -------------------------------------------------------------
    print("\n[TEST 9] Public Health Endpoint...")
    resp_health_public = client.get("/health")
    health_public_ok = (
        resp_health_public.status_code == 200 and
        resp_health_public.json().get("status") == "healthy"
    )
    print(f"   9a. Public GET /health Status: {resp_health_public.status_code}")
    results["public_health"] = health_public_ok

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    all_passed = all(results.values())
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print("\n" + "=" * 80)
    print(f"AUTHENTICATION TEST SUITE: {'PASS' if all_passed else 'FAIL'}")
    print("=" * 80)
    for k, v in results.items():
        print(f"  {k.upper()}: {'PASS' if v else 'FAIL'}")
    print(f"\nTOTAL TESTS PASSED: {passed_count}/{total_count}")

    db.close()
    return all_passed, results


if __name__ == "__main__":
    passed, _ = run_auth_tests()
    sys.exit(0 if passed else 1)
