from fastapi.testclient import TestClient
from web.server import app

client = TestClient(app)

def test_read_write_settings():
    response = client.post("/api/settings/test", params={"value": "123"})
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "123"

    response = client.get("/api/settings/test")
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "123"
