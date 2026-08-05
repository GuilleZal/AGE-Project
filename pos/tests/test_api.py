import pytest
from fastapi.testclient import TestClient
from pos.server import app

client = TestClient(app)

def test_api_health():
    """Test that the API health endpoint works."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "POS Server is running"}

def test_api_login_validation_failure():
    """Test login endpoint validation constraints (blank credentials)."""
    response = client.post("/api/auth/login", json={"username": "", "password": ""})
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is False
    assert "Complete todos los campos" in res_data["error"]

def test_api_login_failure():
    """Test login endpoint with incorrect credentials."""
    response = client.post("/api/auth/login", json={"username": "wrong_user", "password": "wrong_password"})
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is False
    assert "incorrectos" in res_data["error"]
