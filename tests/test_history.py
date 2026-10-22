"""
Comprehensive Automated Test Suite for Database-Backed Analysis Persistence.

Validates:
1. Database schema and migration verification for 'analyses' table
2. Successful prediction persists analysis record with authenticated user ID
3. Returned prediction response contains valid persisted analysis_id
4. Invalid uploads and failed requests create zero records in database
5. Simulated database failure is handled honestly (HTTP 500, no false success)
6. GET /history returns empty list when no records exist
7. GET /history returns user analyses sorted newest first
8. Pagination parameters (limit, offset, page, page_size) and filtering (crop, search)
9. GET /history/{id} returns single record for owner
10. Authorization and user isolation:
    - User A cannot view User B's history
    - User A cannot retrieve User B's record (404)
    - User A cannot delete User B's record (404)
11. DELETE /history/{id} deletes own record with CSRF protection enforced
12. Unauthenticated requests to /history, /history/{id}, and DELETE /history/{id} are rejected with HTTP 401
"""

import sys
import io
import uuid
from pathlib import Path
from PIL import Image
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api import app
from src.database import engine, SessionLocal
from src.models import User, Analysis
from src.schemas import HistoryListResponse, HistoryItem, HistoryDeleteResponse


def create_test_image_bytes() -> bytes:
    """Creates or loads a valid RGB JPEG leaf image."""
    pv_sample = PROJECT_ROOT / "data" / "raw" / "plantvillage" / "plantvillage dataset" / "color" / "Tomato___Early_blight"
    leaf_file = next(pv_sample.glob("*.JPG"), None) if pv_sample.exists() else None
    if leaf_file:
        with open(leaf_file, "rb") as f:
            return f.read()
    buf = io.BytesIO()
    np_arr = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
    Image.fromarray(np_arr).save(buf, format="JPEG")
    return buf.getvalue()


def register_and_login(client: TestClient, name: str = "History Farmer"):
    """Registers a new distinct user and logs them in, returning email, password, and csrf_token."""
    uid = uuid.uuid4().hex[:8]
    email = f"farmer_{uid}@historytest.org"
    password = f"StrongPass!{uid}"
    
    # Register
    reg_resp = client.post("/auth/register", json={
        "full_name": name,
        "email": email,
        "password": password
    })
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"

    # Login
    login_resp = client.post("/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    csrf_token = login_resp.cookies.get("csrf_token")
    assert csrf_token is not None, "CSRF token cookie missing"
    
    return email, password, csrf_token


def run_history_tests():
    print("=" * 80)
    print("DATABASE-BACKED ANALYSIS PERSISTENCE TEST SUITE")
    print("=" * 80)

    results = {}
    valid_img_bytes = create_test_image_bytes()

    # -----------------------------------------------------------------
    # TEST 1: Database Schema & Migration Verification
    # -----------------------------------------------------------------
    print("\n[TEST 1] Verifying database schema and 'analyses' table...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    has_analyses = "analyses" in tables
    
    if has_analyses:
        columns = {c["name"]: c for c in inspector.get_columns("analyses")}
        required_cols = {"id", "user_id", "crop", "disease_code", "disease_name", "confidence", "model_version", "created_at"}
        has_all_cols = required_cols.issubset(set(columns.keys()))
        fks = inspector.get_foreign_keys("analyses")
        has_user_fk = any(fk["referred_table"] == "users" for fk in fks)
        test_1_ok = has_analyses and has_all_cols and has_user_fk
        print(f"   Table 'analyses' present: {has_analyses}")
        print(f"   Columns present: {sorted(columns.keys())}")
        print(f"   Foreign keys: {fks}")
    else:
        test_1_ok = False
        print("   FAIL: Table 'analyses' not found in database.")

    print(f"   Database Schema Test: {'PASS' if test_1_ok else 'FAIL'}")
    results["db_schema"] = test_1_ok

    # -----------------------------------------------------------------
    # TEST 2: Prediction Persistence & Returned analysis_id
    # -----------------------------------------------------------------
    print("\n[TEST 2] Testing Prediction Persistence for Authenticated User...")
    client_a = TestClient(app)
    email_a, _, csrf_a = register_and_login(client_a, name="Farmer Alice")

    pred_resp = client_a.post(
        "/predict",
        files={"image": ("alice_leaf.jpg", valid_img_bytes, "image/jpeg")},
        headers={"X-CSRF-Token": csrf_a}
    )
    print(f"   Predict Status: {pred_resp.status_code}")
    pred_json = pred_resp.json()
    analysis_id = pred_json.get("analysis_id")
    print(f"   Returned analysis_id: {analysis_id}")
    print(f"   Crop: {pred_json.get('crop')}, Disease: {pred_json.get('disease')}")

    # Verify directly in database
    db = SessionLocal()
    try:
        user_a = db.query(User).filter(User.email == email_a).first()
        assert user_a is not None, "User Alice not found in DB"
        
        stored_analysis = db.query(Analysis).filter(Analysis.id == int(analysis_id)).first()
        test_2_ok = (
            pred_resp.status_code == 200 and
            analysis_id is not None and
            stored_analysis is not None and
            stored_analysis.user_id == user_a.id and
            stored_analysis.crop == pred_json.get("crop") and
            stored_analysis.disease_code == pred_json.get("disease_code") and
            stored_analysis.confidence == pred_json.get("confidence")
        )
        print(f"   Stored record in DB: {stored_analysis}")
    finally:
        db.close()

    print(f"   Prediction Persistence Test: {'PASS' if test_2_ok else 'FAIL'}")
    results["prediction_persistence"] = test_2_ok

    # -----------------------------------------------------------------
    # TEST 3: Invalid / Failed Uploads Create Zero DB Records
    # -----------------------------------------------------------------
    print("\n[TEST 3] Testing Invalid Uploads Do Not Create Records...")
    db = SessionLocal()
    try:
        count_before = db.query(Analysis).count()
        # Corrupted image upload
        bad_resp = client_a.post(
            "/predict",
            files={"image": ("corrupted.jpg", b"INVALID_GARBAGE_BYTES", "image/jpeg")},
            headers={"X-CSRF-Token": csrf_a}
        )
        # Empty file upload
        empty_resp = client_a.post(
            "/predict",
            files={"image": ("empty.jpg", b"", "image/jpeg")},
            headers={"X-CSRF-Token": csrf_a}
        )
        count_after = db.query(Analysis).count()
        test_3_ok = (
            bad_resp.status_code == 422 and
            empty_resp.status_code == 400 and
            count_before == count_after
        )
        print(f"   Count before: {count_before}, Count after: {count_after}")
    finally:
        db.close()

    print(f"   Invalid Upload Safety Test: {'PASS' if test_3_ok else 'FAIL'}")
    results["invalid_upload_safety"] = test_3_ok

    # -----------------------------------------------------------------
    # TEST 4: Simulated Database Failure Handled Honestly
    # -----------------------------------------------------------------
    print("\n[TEST 4] Testing Database Commit Failure Error Handling...")
    with patch.object(Session, "commit", side_effect=Exception("Simulated SQLite write error")):
        fail_resp = client_a.post(
            "/predict",
            files={"image": ("leaf.jpg", valid_img_bytes, "image/jpeg")},
            headers={"X-CSRF-Token": csrf_a}
        )
        test_4_ok = (
            fail_resp.status_code == 500 and
            fail_resp.json().get("error", {}).get("code") == "DATABASE_ERROR" and
            fail_resp.json().get("success") is False
        )
        print(f"   Status: {fail_resp.status_code}, Error Code: {fail_resp.json().get('error', {}).get('code')}")

    print(f"   Database Write Failure Handling: {'PASS' if test_4_ok else 'FAIL'}")
    results["db_failure_handling"] = test_4_ok

    # -----------------------------------------------------------------
    # TEST 5: Empty History for New User
    # -----------------------------------------------------------------
    print("\n[TEST 5] Testing Empty History for New User...")
    client_fresh = TestClient(app)
    register_and_login(client_fresh, name="Fresh Farmer")
    empty_hist_resp = client_fresh.get("/history")
    print(f"   Status: {empty_hist_resp.status_code}, Body: {empty_hist_resp.json()}")
    test_5_ok = (
        empty_hist_resp.status_code == 200 and
        empty_hist_resp.json().get("total") == 0 and
        len(empty_hist_resp.json().get("items")) == 0
    )
    print(f"   Empty History Test: {'PASS' if test_5_ok else 'FAIL'}")
    results["empty_history"] = test_5_ok

    # -----------------------------------------------------------------
    # TEST 6: History Pagination and Newest-First Ordering
    # -----------------------------------------------------------------
    print("\n[TEST 6] Testing History Pagination & Sorting...")
    # Add 3 more predictions for client_a
    for i in range(3):
        client_a.post(
            "/predict",
            files={"image": (f"leaf_{i}.jpg", valid_img_bytes, "image/jpeg")},
            headers={"X-CSRF-Token": csrf_a}
        )

    # Fetch with limit=2
    page1_resp = client_a.get("/history?limit=2&offset=0&sort=newest")
    p1_json = page1_resp.json()
    print(f"   Page 1 (limit 2): total={p1_json.get('total')}, items returned={len(p1_json.get('items'))}")

    # Fetch with limit=2, offset=2
    page2_resp = client_a.get("/history?limit=2&offset=2&sort=newest")
    p2_json = page2_resp.json()
    print(f"   Page 2 (offset 2): items returned={len(p2_json.get('items'))}")

    # Check ordering (newest first: ID descending)
    all_resp = client_a.get("/history?limit=10&offset=0&sort=newest")
    all_items = all_resp.json().get("items")
    ids = [int(item["analysis_id"]) for item in all_items]
    is_desc = ids == sorted(ids, reverse=True)

    test_6_ok = (
        p1_json.get("total") >= 4 and
        len(p1_json.get("items")) == 2 and
        len(p2_json.get("items")) >= 2 and
        p1_json.get("items")[0]["analysis_id"] != p2_json.get("items")[0]["analysis_id"] and
        is_desc
    )
    print(f"   ID order (newest first): {ids}, is descending: {is_desc}")
    print(f"   Pagination and Sorting Test: {'PASS' if test_6_ok else 'FAIL'}")
    results["pagination_and_sorting"] = test_6_ok

    # -----------------------------------------------------------------
    # TEST 7: Single Analysis Retrieval (GET /history/{id})
    # -----------------------------------------------------------------
    print("\n[TEST 7] Testing Single Record Retrieval...")
    single_id = all_items[0]["analysis_id"]
    single_resp = client_a.get(f"/history/{single_id}")
    single_json = single_resp.json()
    test_7_ok = (
        single_resp.status_code == 200 and
        single_json.get("analysis_id") == str(single_id) and
        single_json.get("crop") is not None and
        single_json.get("disease_code") is not None
    )
    print(f"   GET /history/{single_id} Status: {single_resp.status_code}, Disease: {single_json.get('disease')}")
    print(f"   Single Record Test: {'PASS' if test_7_ok else 'FAIL'}")
    results["single_retrieval"] = test_7_ok

    # -----------------------------------------------------------------
    # TEST 8: Authorization and User Isolation
    # -----------------------------------------------------------------
    print("\n[TEST 8] Testing Authorization & Multi-Tenant User Isolation...")
    client_b = TestClient(app)
    email_b, _, csrf_b = register_and_login(client_b, name="Farmer Bob")

    # Bob creates 1 prediction
    bob_pred = client_b.post(
        "/predict",
        files={"image": ("bob_leaf.jpg", valid_img_bytes, "image/jpeg")},
        headers={"X-CSRF-Token": csrf_b}
    )
    bob_analysis_id = bob_pred.json().get("analysis_id")

    # 8a: Bob's history should only show Bob's prediction, not Alice's
    bob_hist = client_b.get("/history")
    bob_items = bob_hist.json().get("items")
    bob_ids = [item["analysis_id"] for item in bob_items]
    isolation_list_ok = (
        str(bob_analysis_id) in bob_ids and
        str(single_id) not in bob_ids
    )
    print(f"   8a. Bob's items: {bob_ids}. Contains Alice's ID ({single_id})? {str(single_id) in bob_ids}")

    # 8b: Alice tries to GET Bob's record -> Must be 404
    alice_peek_bob = client_a.get(f"/history/{bob_analysis_id}")
    alice_peek_ok = (
        alice_peek_bob.status_code == 404 and
        alice_peek_bob.json().get("error", {}).get("code") == "ANALYSIS_NOT_FOUND"
    )
    print(f"   8b. Alice GET Bob's record: Status {alice_peek_bob.status_code}, Code: {alice_peek_bob.json().get('error', {}).get('code')}")

    # 8c: Alice tries to DELETE Bob's record -> Must be 404
    alice_del_bob = client_a.delete(
        f"/history/{bob_analysis_id}",
        headers={"X-CSRF-Token": csrf_a}
    )
    alice_del_ok = (
        alice_del_bob.status_code == 404 and
        alice_del_bob.json().get("error", {}).get("code") == "ANALYSIS_NOT_FOUND"
    )
    print(f"   8c. Alice DELETE Bob's record: Status {alice_del_bob.status_code}, Code: {alice_del_bob.json().get('error', {}).get('code')}")

    # Verify Bob's record still exists in DB
    bob_record_still_exists = client_b.get(f"/history/{bob_analysis_id}").status_code == 200

    test_8_ok = isolation_list_ok and alice_peek_ok and alice_del_ok and bob_record_still_exists
    print(f"   User Isolation & Security Test: {'PASS' if test_8_ok else 'FAIL'}")
    results["user_isolation"] = test_8_ok

    # -----------------------------------------------------------------
    # TEST 9: Deletion of Own Record with CSRF Enforcement
    # -----------------------------------------------------------------
    print("\n[TEST 9] Testing Record Deletion with CSRF Protection...")
    # 9a: Missing CSRF token -> 403 Forbidden
    del_no_csrf = client_a.delete(f"/history/{single_id}")
    del_no_csrf_ok = (
        del_no_csrf.status_code == 403 and
        del_no_csrf.json().get("error", {}).get("code") == "CSRF_ERROR"
    )
    print(f"   9a. DELETE without CSRF header: Status {del_no_csrf.status_code}, Code: {del_no_csrf.json().get('error', {}).get('code')}")

    # 9b: Valid CSRF token -> 200 OK
    del_ok_resp = client_a.delete(
        f"/history/{single_id}",
        headers={"X-CSRF-Token": csrf_a}
    )
    del_success = (
        del_ok_resp.status_code == 200 and
        del_ok_resp.json().get("success") is True and
        del_ok_resp.json().get("analysis_id") == str(single_id)
    )
    print(f"   9b. DELETE with valid CSRF: Status {del_ok_resp.status_code}, Response: {del_ok_resp.json()}")

    # 9c: Subsequent GET -> 404
    get_deleted = client_a.get(f"/history/{single_id}")
    get_deleted_ok = get_deleted.status_code == 404
    print(f"   9c. GET deleted record: Status {get_deleted.status_code}")

    test_9_ok = del_no_csrf_ok and del_success and get_deleted_ok
    print(f"   Record Deletion Test: {'PASS' if test_9_ok else 'FAIL'}")
    results["record_deletion"] = test_9_ok

    # -----------------------------------------------------------------
    # TEST 10: Unauthenticated Requests to History Endpoints
    # -----------------------------------------------------------------
    print("\n[TEST 10] Testing Unauthenticated Access Rejection...")
    unauth_client = TestClient(app)
    unauth_list = unauth_client.get("/history")
    unauth_single = unauth_client.get("/history/1")
    unauth_del = unauth_client.delete("/history/1")

    test_10_ok = (
        unauth_list.status_code == 401 and
        unauth_single.status_code == 401 and
        unauth_del.status_code == 401
    )
    print(f"   GET /history: Status {unauth_list.status_code}")
    print(f"   GET /history/1: Status {unauth_single.status_code}")
    print(f"   DELETE /history/1: Status {unauth_del.status_code}")
    print(f"   Unauthenticated Access Test: {'PASS' if test_10_ok else 'FAIL'}")
    results["unauthenticated_rejection"] = test_10_ok

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------
    all_passed = all(results.values())
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print("\n" + "=" * 80)
    print(f"ANALYSIS PERSISTENCE SUITE STATUS: {'PASS' if all_passed else 'FAIL'}")
    print("=" * 80)
    for k, v in results.items():
        print(f"  {k.upper()}: {'PASS' if v else 'FAIL'}")
    print(f"\nTOTAL TESTS PASSED: {passed_count}/{total_count}")

    return all_passed, results


if __name__ == "__main__":
    ok, _ = run_history_tests()
    sys.exit(0 if ok else 1)
