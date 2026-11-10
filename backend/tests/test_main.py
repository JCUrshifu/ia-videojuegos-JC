from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"estado": "ok"}

def test_salud_db():
    response = client.get("/salud")
    assert response.status_code in [200, 500]
    data = response.json()
    assert "estado" in data

def test_login_fallido():
    response = client.post("/auth/login", data={"username": "falso@videojuegos.com", "password": "wrongpassword"})
    assert response.status_code in [400, 401]