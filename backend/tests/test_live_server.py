"""
Live network socket verification for FastAPI backend.
Launches uvicorn in a subprocess, tests endpoints over HTTP, and shuts down cleanly.
"""

import sys
import time
import subprocess
from pathlib import Path
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def test_live():
    python_exe = sys.executable
    print("Starting uvicorn server on http://127.0.0.1:8000...")
    proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        # Poll for server readiness up to 15 seconds
        client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=5.0)
        ready = False
        for i in range(15):
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                print("Server exited early! Stdout:", stdout.decode("utf-8", errors="ignore"))
                print("Stderr:", stderr.decode("utf-8", errors="ignore"))
                raise RuntimeError("Server exited before becoming ready.")
            try:
                resp = client.get("/health")
                if resp.status_code == 200:
                    ready = True
                    break
            except Exception:
                time.sleep(1)

        if not ready:
            raise RuntimeError("Server did not become ready within 15 seconds.")

        print("Live GET /health status:", resp.status_code)
        print("Live GET /health json:", resp.json())
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
        assert resp.json()["model_loaded"] is True
        print("Live server /health check: SUCCESS")

        # 1. Verify unauthenticated POST /predict is rejected
        unauth_resp = client.post("/predict")
        assert unauth_resp.status_code == 401
        assert unauth_resp.json().get("error", {}).get("code") == "UNAUTHORIZED"
        print("Live unauthenticated /predict rejection: SUCCESS (401)")

        # 2. Register a new user over socket
        import uuid
        test_email = f"live_{uuid.uuid4().hex[:8]}@example.com"
        reg_resp = client.post("/auth/register", json={
            "full_name": "Live Test Farmer",
            "email": test_email,
            "password": "StrongPassword123!"
        })
        assert reg_resp.status_code == 201
        print("Live POST /auth/register: SUCCESS (201)")

        # 3. Login over socket
        login_resp = client.post("/auth/login", json={
            "email": test_email,
            "password": "StrongPassword123!"
        })
        assert login_resp.status_code == 200
        assert "session_id" in client.cookies
        assert "csrf_token" in client.cookies
        csrf_token = client.cookies["csrf_token"]
        print("Live POST /auth/login: SUCCESS (200)")

        # 4. Get current user
        me_resp = client.get("/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == test_email
        assert "password" not in me_resp.json()
        assert "password_hash" not in me_resp.json()
        print("Live GET /auth/me: SUCCESS (200)")

        # 4b. Check empty history
        hist_empty = client.get("/history")
        assert hist_empty.status_code == 200
        assert hist_empty.json()["total"] == 0
        print("Live empty GET /history: SUCCESS (200)")

        # 4c. Make prediction and check persistence
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (224, 224), color=(34, 139, 34)).save(buf, format="JPEG")
        pred_resp = client.post(
            "/predict",
            files={"image": ("live_leaf.jpg", buf.getvalue(), "image/jpeg")},
            headers={"X-CSRF-Token": csrf_token}
        )
        assert pred_resp.status_code == 200
        saved_id = pred_resp.json().get("analysis_id")
        assert saved_id is not None
        print(f"Live POST /predict: SUCCESS (saved analysis_id={saved_id})")

        # 4d. Fetch history containing the new analysis
        hist_populated = client.get("/history")
        assert hist_populated.status_code == 200
        assert hist_populated.json()["total"] >= 1
        assert any(item["analysis_id"] == str(saved_id) for item in hist_populated.json()["items"])
        print("Live populated GET /history: SUCCESS (200)")

        # 4e. Single analysis retrieval
        single_analysis = client.get(f"/history/{saved_id}")
        assert single_analysis.status_code == 200
        assert single_analysis.json()["analysis_id"] == str(saved_id)
        print(f"Live GET /history/{saved_id}: SUCCESS (200)")

        # 4f. Delete analysis record
        del_analysis = client.post(f"/history/{saved_id}", headers={"X-CSRF-Token": csrf_token}) # test 405 or method
        del_resp = client.delete(f"/history/{saved_id}", headers={"X-CSRF-Token": csrf_token})
        assert del_resp.status_code == 200
        print(f"Live DELETE /history/{saved_id}: SUCCESS (200)")

        # 4g. Verify deleted analysis returns 404
        post_del = client.get(f"/history/{saved_id}")
        assert post_del.status_code == 404
        print(f"Live deleted record 404 check: SUCCESS")

        # 5. Logout
        logout_resp = client.post("/auth/logout", headers={"X-CSRF-Token": csrf_token})
        assert logout_resp.status_code == 200
        print("Live POST /auth/logout: SUCCESS (200)")

        # 6. Post-logout /auth/me is rejected
        post_logout_me = client.get("/auth/me")
        assert post_logout_me.status_code == 401
        print("Live post-logout /auth/me rejection: SUCCESS (401)")

        print("All live server socket tests: SUCCESS")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Server stopped cleanly.")

if __name__ == "__main__":
    test_live()
