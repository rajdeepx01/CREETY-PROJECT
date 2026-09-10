import sys
import os
import io
import json
import uuid
from pathlib import Path

# Force UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
from httpx import AsyncClient, ASGITransport
from PIL import Image
from backend.app.main import app
from backend.app.database import init_db

async def run_tests():
    print("[*] Initializing test database...")
    await init_db()
    
    unique_suffix = uuid.uuid4().hex[:6]
    username_a = f"sarah_{unique_suffix}"
    email_a = f"sarah_{unique_suffix}@example.com"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\n--- 1. Healthcheck Test ---")
        res = await client.get("/api/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("[PASS] Healthcheck passed:", res.json())

        print("\n--- 2. User Registration Test ---")
        user_a = {
            "email": email_a,
            "username": username_a,
            "password": "SuperSecretPassword123!",
            "full_name": "Sarah Connor"
        }
        res = await client.post("/api/auth/register", json=user_a)
        assert res.status_code == 200, f"Registration failed: {res.text}"
        data_a = res.json()
        token_a = data_a["access_token"]
        assert token_a is not None
        assert data_a["user"]["username"] == username_a
        print("[PASS] Registration passed! User ID:", data_a["user"]["id"])

        print("\n--- 3. Email Verification Sandbox Test ---")
        res = await client.get("/api/auth/mailbox")
        assert res.status_code == 200
        mailbox = res.json()["emails"]
        assert len(mailbox) > 0
        v_token = mailbox[0]["token"]
        
        # Verify email
        res = await client.post("/api/auth/verify-email", json={"token": v_token})
        assert res.status_code == 200, f"Email verification failed: {res.text}"
        print("[PASS] Email verified successfully with token:", v_token)

        print("\n--- 4. Authentication / Login Test ---")
        res = await client.post("/api/auth/login", json={
            "email_or_username": username_a,
            "password": "SuperSecretPassword123!"
        })
        assert res.status_code == 200, f"Login failed: {res.text}"
        token_a = res.json()["access_token"]
        auth_headers_a = {"Authorization": f"Bearer {token_a}"}
        print("[PASS] Login passed with JWT Access Token!")

        print("\n--- 5. 2FA (TOTP) Setup & Enable Test ---")
        res = await client.get("/api/auth/2fa/setup", headers=auth_headers_a)
        assert res.status_code == 200
        twofa_data = res.json()
        secret = twofa_data["secret"]
        backup_codes = twofa_data["backup_codes"]
        assert len(backup_codes) == 8
        print("[PASS] 2FA setup generated secret:", secret)
        
        # Calculate current TOTP
        import pyotp
        totp = pyotp.TOTP(secret)
        current_code = totp.now()

        res = await client.post("/api/auth/2fa/enable", json={"code": current_code}, headers=auth_headers_a)
        assert res.status_code == 200, f"2FA enable failed: {res.text}"
        print("[PASS] 2FA activated successfully!")

        print("\n--- 6. File Upload Security & Magic-Byte Validation Test ---")
        # 6a. Malicious fake PDF (text content with .pdf extension)
        fake_pdf = io.BytesIO(b"MALICIOUS SCRIPT EXECUTABLE CONTENT")
        res = await client.post(
            "/api/achievements",
            headers=auth_headers_a,
            data={
                "title": "Fake Certificate",
                "category": "Certificate",
                "issuer": "Scam Academy",
                "issue_date": "2026-01-01",
                "is_public": "true"
            },
            files={"file": ("fake.pdf", fake_pdf, "application/pdf")}
        )
        assert res.status_code == 400, f"Expected 400 rejection for fake PDF magic bytes, got {res.status_code}"
        print("[PASS] Magic-byte file security successfully REJECTED fake PDF!")

        # 6b. Valid PNG image with authentic PNG magic header
        img_buf = io.BytesIO()
        test_img = Image.new("RGB", (120, 120), color="#4f46e5")
        test_img.save(img_buf, format="PNG")
        valid_png_bytes = img_buf.getvalue()
        valid_png = io.BytesIO(valid_png_bytes)
        
        res = await client.post(
            "/api/achievements",
            headers=auth_headers_a,
            data={
                "title": "AWS Certified Solutions Architect",
                "category": "Certificate",
                "issuer": "Amazon Web Services",
                "issue_date": "2026-05-15",
                "description": "Demonstrated advanced cloud architecture and security.",
                "credential_id": "AWS-CERT-8849",
                "credential_url": "https://aws.amazon.com/verify",
                "tags": json.dumps(["AWS", "Cloud Architecture", "DevOps"]),
                "is_public": "true"
            },
            files={"file": ("aws_cert.png", valid_png, "image/png")}
        )
        assert res.status_code == 200, f"Valid PNG upload failed: {res.text}"
        ach_pub = res.json()
        assert ach_pub["has_media"] is True
        print("[PASS] Authentic PNG Certificate accepted and stored! Achievement ID:", ach_pub["id"])

        # 6c. Create a Private Achievement
        res = await client.post(
            "/api/achievements",
            headers=auth_headers_a,
            data={
                "title": "Top Secret Internal Defense Award",
                "category": "Award",
                "issuer": "Cyber Command",
                "issue_date": "2026-08-20",
                "description": "Classified achievement for internal eye only.",
                "is_public": "false"
            }
        )
        assert res.status_code == 200
        ach_priv = res.json()
        assert ach_priv["is_public"] is False
        print("[PASS] Private Achievement created! ID:", ach_priv["id"])

        print("\n--- 7. Public Profile & Privacy Isolation Test ---")
        # Unauthenticated guest visits Sarah's public profile
        res = await client.get(f"/api/users/public/{username_a}")
        assert res.status_code == 200
        public_profile = res.json()
        
        # Must only see the public achievement (1 item), private item (Secret Award) must be invisible
        public_items = public_profile["achievements"]
        assert len(public_items) == 1, f"Expected 1 public item, found {len(public_items)}"
        assert public_items[0]["id"] == ach_pub["id"]
        assert all(item["id"] != ach_priv["id"] for item in public_items)
        print(f"[PASS] Privacy verified! Guest can see {len(public_items)} public item(s); private items are completely hidden.")

        print("\n--- 8. Role-Based Access Control (RBAC) Test ---")
        # Create User B (Attacker)
        username_b = f"attacker_{unique_suffix}"
        user_b = {
            "email": f"attacker_{unique_suffix}@example.com",
            "username": username_b,
            "password": "AttackerPassword123!",
            "full_name": "Bad Actor"
        }
        res = await client.post("/api/auth/register", json=user_b)
        token_b = res.json()["access_token"]
        auth_headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B attempts to delete User A's achievement
        res = await client.delete(f"/api/achievements/{ach_pub['id']}", headers=auth_headers_b)
        assert res.status_code == 403, f"Expected 403 Forbidden for cross-user delete, got {res.status_code}"
        print("[PASS] RBAC verified! User B cannot delete User A's achievement (403 Forbidden).")

        print("\n--- 9. Achievement Media Stream Test ---")
        res = await client.get(f"/api/achievements/media/{ach_pub['id']}")
        assert res.status_code == 200
        assert res.headers["x-content-type-options"] == "nosniff"
        assert len(res.content) == len(valid_png_bytes)
        print("[PASS] Media stream verified with secure headers!")

        print("\n=======================================================")
        print(" [SUCCESS] ALL 9 BACKEND & SECURITY TESTS PASSED 100%!")
        print("=======================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
