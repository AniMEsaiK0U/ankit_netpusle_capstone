import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient


TEST_USERNAME = "test-user"
TEST_PASSWORD = secrets.token_urlsafe(24)
TEST_SECRET = secrets.token_urlsafe(48)
os.environ["DEMO_USERNAME"] = TEST_USERNAME
os.environ["DEMO_PASSWORD"] = TEST_PASSWORD
os.environ["JWT_SECRET"] = TEST_SECRET

from api.main import app


client = TestClient(app)
device_payload = {
    "name": "Edge Router",
    "device_type": "router",
    "status": "online",
    "location": "Test Lab",
}


def test_public_reads_and_authenticated_crud_lifecycle() -> None:
    devices_response = client.get("/devices")
    assert devices_response.status_code == 200
    assert len(devices_response.json()) >= 2
    assert client.get("/devices/1").status_code == 200
    assert client.get("/devices/999").status_code == 404

    assert client.post("/devices", json=device_payload).status_code == 401
    assert (
        client.post(
            "/devices",
            json=device_payload,
            headers={"Authorization": "Bearer invalid-token"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/token",
            data={"username": TEST_USERNAME, "password": "incorrect"},
        ).status_code
        == 401
    )

    login_response = client.post(
        "/auth/token",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    claims = jwt.decode(access_token, TEST_SECRET, algorithms=["HS256"])
    assert claims["sub"] == TEST_USERNAME
    assert claims["exp"] > datetime.now(timezone.utc).timestamp()
    headers = {"Authorization": f"Bearer {access_token}"}

    unrelated_subject_token = jwt.encode(
        {
            "sub": "another-user",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        TEST_SECRET,
        algorithm="HS256",
    )
    assert (
        client.post(
            "/devices",
            json=device_payload,
            headers={"Authorization": f"Bearer {unrelated_subject_token}"},
        ).status_code
        == 401
    )

    created = client.post("/devices", json=device_payload, headers=headers)
    assert created.status_code == 201
    device_id = created.json()["id"]

    replacement = {**device_payload, "name": "Updated Edge Router"}
    replaced = client.put(
        f"/devices/{device_id}", json=replacement, headers=headers
    )
    assert replaced.status_code == 200
    assert replaced.json()["id"] == device_id

    patched = client.patch(
        f"/devices/{device_id}",
        json={"status": "maintenance"},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "maintenance"
    assert patched.json()["name"] == "Updated Edge Router"

    deleted = client.delete(f"/devices/{device_id}", headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(f"/devices/{device_id}").status_code == 404