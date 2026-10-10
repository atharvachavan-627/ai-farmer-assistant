"""
Frontend-Backend Integration Test Suite for AI Farmer Assistant.

Validates the exact integration contracts expected by the React + Vite frontend:
1. Registration contract: { name, email, password } -> { success, user: { id, full_name, name, email } }
2. Login contract: { email, password } -> sets HttpOnly session_id and csrf_token cookies
3. Session verification: GET /auth/me -> returns user matching unwrapUser schema (id, name, email)
4. UI Preferences sync: GET & PUT /users/me/preferences { language: 'en' | 'hi' | 'mr' }
5. Leaf Analysis: POST /predict with multipart 'image' & CSRF header -> normalisePrediction shape
6. History List: GET /history with { page, page_size, sort } -> normaliseRecord shape, total, pagination
7. Single Analysis & Delete: GET /history/{id} and DELETE /history/{id} with CSRF token
8. Multi-tenant user isolation: User A cannot view, retrieve, or delete User B's records
9. Logout & session invalidation: POST /auth/logout clears cookies, subsequent requests return 401
10. Upstream dependency verification: GET /diseases returns 404, gracefully handled by frontend ErrorState
"""

import sys
import io
import uuid
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api import app


def make_leaf_image() -> bytes:
    """Generate dummy leaf image bytes."""
    buf = io.BytesIO()
    Image.new("RGB", (224, 224), color=(34, 139, 34)).save(buf, format="JPEG")
    return buf.getvalue()


def run_integration_audit():
    print("=" * 80)
    print("FRONTEND-BACKEND INTEGRATION AUDIT & TEST SUITE")
    print("=" * 80)

    client = TestClient(app)
    results = {}
    leaf_bytes = make_leaf_image()

    uid = uuid.uuid4().hex[:8]
    test_name = f"Ramesh Farmer {uid}"
    test_email = f"farmer_{uid}@example.com"
    test_pass = f"Pass_{uid}!123"

    # -------------------------------------------------------------
    # 1. Registration Contract (authService.register)
    # -------------------------------------------------------------
    print("\n[CHECK 1] Testing authService.register contract { name, email, password }...")
    reg_payload = {
        "name": test_name,
        "email": test_email,
        "password": test_pass
    }
    reg_resp = client.post("/auth/register", json=reg_payload)
    print(f"   Status: {reg_resp.status_code}")
    reg_data = reg_resp.json()
    user_data = reg_data.get("user", {})
    
    check_1_ok = (
        reg_resp.status_code == 201 and
        reg_data.get("success") is True and
        user_data.get("email") == test_email and
        (user_data.get("name") == test_name or user_data.get("full_name") == test_name)
    )
    print(f"   User returned: id={user_data.get('id')}, full_name='{user_data.get('full_name')}', name='{user_data.get('name')}'")
    print(f"   Registration Contract: {'PASS' if check_1_ok else 'FAIL'}")
    results["registration_contract"] = check_1_ok

    # -------------------------------------------------------------
    # 2. Login Contract (authService.login)
    # -------------------------------------------------------------
    print("\n[CHECK 2] Testing authService.login contract { email, password }...")
    login_resp = client.post("/auth/login", json={"email": test_email, "password": test_pass})
    print(f"   Status: {login_resp.status_code}")
    session_cookie = login_resp.cookies.get("session_id")
    csrf_cookie = login_resp.cookies.get("csrf_token")
    
    check_2_ok = (
        login_resp.status_code == 200 and
        session_cookie is not None and
        csrf_cookie is not None and
        login_resp.json().get("success") is True
    )
    print(f"   HttpOnly session cookie: {'Present' if session_cookie else 'MISSING'}")
    print(f"   CSRF token cookie: {'Present' if csrf_cookie else 'MISSING'}")
    print(f"   Login Contract: {'PASS' if check_2_ok else 'FAIL'}")
    results["login_contract"] = check_2_ok

    # -------------------------------------------------------------
    # 3. Current User Contract (authService.getCurrentUser)
    # -------------------------------------------------------------
    print("\n[CHECK 3] Testing authService.getCurrentUser contract (GET /auth/me)...")
    me_resp = client.get("/auth/me")
    me_data = me_resp.json()
    print(f"   Status: {me_resp.status_code}, User: {me_data}")
    
    # Frontend unwrapUser expects (u.email || u.id) and Home greeting uses user.name
    check_3_ok = (
        me_resp.status_code == 200 and
        me_data.get("email") == test_email and
        me_data.get("name") is not None and
        me_data.get("id") is not None and
        "password" not in me_data and
        "password_hash" not in me_data
    )
    print(f"   Current User Contract: {'PASS' if check_3_ok else 'FAIL'}")
    results["current_user_contract"] = check_3_ok

    # -------------------------------------------------------------
    # 4. User Preferences Contract (preferenceService.get & update)
    # -------------------------------------------------------------
    print("\n[CHECK 4] Testing preferenceService UI language sync...")
    pref_get = client.get("/users/me/preferences")
    print(f"   Initial preferences: {pref_get.json()}")
    pref_put = client.put(
        "/users/me/preferences",
        json={"language": "mr"},
        headers={"X-CSRF-Token": csrf_cookie}
    )
    print(f"   Updated preferences: {pref_put.json()}")
    
    check_4_ok = (
        pref_get.status_code == 200 and
        pref_put.status_code == 200 and
        pref_put.json().get("language") == "mr"
    )
    print(f"   Preferences Sync Contract: {'PASS' if check_4_ok else 'FAIL'}")
    results["preferences_contract"] = check_4_ok

    # -------------------------------------------------------------
    # 5. Analyse Predict Contract (analysisService.predict)
    # -------------------------------------------------------------
    print("\n[CHECK 5] Testing analysisService.predict contract (POST /predict with multipart 'image')...")
    pred_resp = client.post(
        "/predict",
        files={"image": ("farm_leaf.jpg", leaf_bytes, "image/jpeg")},
        headers={"X-CSRF-Token": csrf_cookie}
    )
    print(f"   Status: {pred_resp.status_code}")
    pdata = pred_resp.json()
    
    # Frontend normalisePrediction checks:
    # d.success !== false, d.disease_code, analysis_id, crop, confidence, treatment
    t = pdata.get("treatment", {})
    check_5_ok = (
        pred_resp.status_code == 200 and
        pdata.get("success") is True and
        pdata.get("disease_code") is not None and
        pdata.get("analysis_id") is not None and
        pdata.get("confidence") is not None and
        t.get("summary") is not None and
        isinstance(t.get("preventive_measures"), list) and
        isinstance(t.get("organic_treatment"), list) and
        isinstance(t.get("chemical_treatment"), list)
    )
    saved_analysis_id = pdata.get("analysis_id")
    print(f"   Saved analysis_id: {saved_analysis_id}")
    print(f"   Disease: {pdata.get('disease')} (Conf: {pdata.get('confidence')})")
    print(f"   Analyse Prediction Contract: {'PASS' if check_5_ok else 'FAIL'}")
    results["predict_contract"] = check_5_ok

    # -------------------------------------------------------------
    # 6. History List Contract (historyService.list)
    # -------------------------------------------------------------
    print("\n[CHECK 6] Testing historyService.list contract (GET /history?page=1&page_size=12)...")
    hist_resp = client.get("/history?page=1&page_size=12&sort=newest")
    print(f"   Status: {hist_resp.status_code}")
    hdata = hist_resp.json()
    items = hdata.get("items", [])
    
    check_6_ok = (
        hist_resp.status_code == 200 and
        isinstance(items, list) and
        len(items) >= 1 and
        hdata.get("total") >= 1 and
        items[0].get("analysis_id") == str(saved_analysis_id) and
        items[0].get("crop") is not None and
        items[0].get("disease") is not None and
        items[0].get("created_at") is not None
    )
    print(f"   Total items: {hdata.get('total')}, Page: {hdata.get('page')}, PageSize: {hdata.get('page_size')}")
    print(f"   Latest item: {items[0] if items else 'None'}")
    print(f"   History List Contract: {'PASS' if check_6_ok else 'FAIL'}")
    results["history_list_contract"] = check_6_ok

    # -------------------------------------------------------------
    # 7. Single Analysis & Delete (historyService & HistoryCard)
    # -------------------------------------------------------------
    print(f"\n[CHECK 7] Testing Single Analysis Retrieval & Deletion (ID: {saved_analysis_id})...")
    single_resp = client.get(f"/history/{saved_analysis_id}")
    print(f"   GET /history/{saved_analysis_id} Status: {single_resp.status_code}")
    
    del_resp = client.delete(
        f"/history/{saved_analysis_id}",
        headers={"X-CSRF-Token": csrf_cookie}
    )
    print(f"   DELETE /history/{saved_analysis_id} Status: {del_resp.status_code}")
    
    post_del_resp = client.get(f"/history/{saved_analysis_id}")
    print(f"   Post-delete GET Status: {post_del_resp.status_code}")
    
    check_7_ok = (
        single_resp.status_code == 200 and
        del_resp.status_code == 200 and
        post_del_resp.status_code == 404
    )
    print(f"   History Retrieval & Deletion: {'PASS' if check_7_ok else 'FAIL'}")
    results["single_and_delete"] = check_7_ok

    # -------------------------------------------------------------
    # 8. Multi-Tenant User Isolation
    # -------------------------------------------------------------
    print("\n[CHECK 8] Testing Multi-Tenant User Isolation...")
    client_b = TestClient(app)
    uid_b = uuid.uuid4().hex[:8]
    client_b.post("/auth/register", json={"name": f"Farmer B {uid_b}", "email": f"b_{uid_b}@farm.org", "password": f"PassB_{uid_b}!123"})
    login_b = client_b.post("/auth/login", json={"email": f"b_{uid_b}@farm.org", "password": f"PassB_{uid_b}!123"})
    csrf_b = login_b.cookies.get("csrf_token")
    
    # B creates a record
    pred_b = client_b.post(
        "/predict",
        files={"image": ("b_leaf.jpg", leaf_bytes, "image/jpeg")},
        headers={"X-CSRF-Token": csrf_b}
    )
    b_analysis_id = pred_b.json().get("analysis_id")
    
    # A tries to access B's record
    a_peek = client.get(f"/history/{b_analysis_id}")
    a_del = client.delete(f"/history/{b_analysis_id}", headers={"X-CSRF-Token": csrf_cookie})
    
    check_8_ok = (
        a_peek.status_code == 404 and
        a_del.status_code == 404
    )
    print(f"   User A GET User B's record: Status {a_peek.status_code} (Expected 404)")
    print(f"   User A DELETE User B's record: Status {a_del.status_code} (Expected 404)")
    print(f"   Multi-Tenant User Isolation: {'PASS' if check_8_ok else 'FAIL'}")
    results["user_isolation"] = check_8_ok

    # -------------------------------------------------------------
    # 9. Logout & Session Invalidation (authService.logout)
    # -------------------------------------------------------------
    print("\n[CHECK 9] Testing authService.logout and session invalidation...")
    logout_resp = client.post("/auth/logout", headers={"X-CSRF-Token": csrf_cookie})
    print(f"   POST /auth/logout Status: {logout_resp.status_code}")
    
    post_logout_me = client.get("/auth/me")
    post_logout_predict = client.post("/predict")
    post_logout_history = client.get("/history")
    
    check_9_ok = (
        logout_resp.status_code == 200 and
        post_logout_me.status_code == 401 and
        post_logout_predict.status_code == 401 and
        post_logout_history.status_code == 401
    )
    print(f"   Post-logout /auth/me: {post_logout_me.status_code}")
    print(f"   Post-logout /predict: {post_logout_predict.status_code}")
    print(f"   Post-logout /history: {post_logout_history.status_code}")
    print(f"   Logout & Invalidation Contract: {'PASS' if check_9_ok else 'FAIL'}")
    results["logout_invalidation"] = check_9_ok

    # -------------------------------------------------------------
    # 10. Disease Catalogue Integration (GET /diseases & GET /diseases/{id})
    # -------------------------------------------------------------
    print("\n[CHECK 10] Testing disease catalogue endpoints (GET /diseases)...")
    dis_resp = client.get("/diseases")
    print(f"   GET /diseases Status: {dis_resp.status_code}")
    dis_data = dis_resp.json()
    check_10_ok = dis_resp.status_code == 200 and dis_data.get("total") == 13 and len(dis_data.get("items", [])) == 13
    
    # Also verify single item lookup
    single_resp = client.get("/diseases/Tomato___Early_blight")
    single_ok = single_resp.status_code == 200 and single_resp.json().get("disease_code") == "Tomato___Early_blight"
    check_10_ok = check_10_ok and single_ok

    print(f"   GET /diseases returns 200 with 13 classes: {check_10_ok}")
    print(f"   Disease Endpoint Integration: {'PASS' if check_10_ok else 'FAIL'}")
    results["disease_catalogue_contract"] = check_10_ok

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    all_passed = all(results.values())
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print("\n" + "=" * 80)
    print(f"INTEGRATION AUDIT SUITE STATUS: {'PASS' if all_passed else 'FAIL'}")
    print("=" * 80)
    for k, v in results.items():
        print(f"  {k.upper()}: {'PASS' if v else 'FAIL'}")
    print(f"\nTOTAL CHECKS PASSED: {passed_count}/{total_count}")

    return all_passed, results


if __name__ == "__main__":
    ok, _ = run_integration_audit()
    sys.exit(0 if ok else 1)
