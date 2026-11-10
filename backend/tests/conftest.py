"""Configuración común de las pruebas.

Dos niveles:
- Pruebas de unidad: no necesitan base de datos (se ejecutan siempre, incluso en CI).
- Pruebas de integración: usan fixtures que verifican la BD antes de correr;
  si DATABASE_URL no existe o no responde, se omiten (skip) sin fallar.
"""
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ADMIN = {
    "username": os.getenv("TEST_ADMIN_EMAIL", "admin@videojuegos.com"),
    "password": os.getenv("TEST_ADMIN_PASSWORD", "Admin123"),
}
USUARIO = {
    "username": os.getenv("TEST_USER_EMAIL", "usuario@videojuegos.com"),
    "password": os.getenv("TEST_USER_PASSWORD", "Usuario123"),
}

_bd_disponible = None


def hay_base_de_datos() -> bool:
    """Comprueba una sola vez si DATABASE_URL responde."""
    global _bd_disponible
    if _bd_disponible is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            _bd_disponible = False
        else:
            try:
                import psycopg2
                conn = psycopg2.connect(url, connect_timeout=3)
                conn.close()
                _bd_disponible = True
            except Exception:
                _bd_disponible = False
    return _bd_disponible


def requiere_bd():
    if not hay_base_de_datos():
        pytest.skip("Base de datos no disponible: prueba de integración omitida")


def _login(credenciales: dict) -> dict:
    requiere_bd()
    r = client.post("/auth/login", data=credenciales)
    assert r.status_code == 200, f"Login falló ({credenciales['username']}): {r.status_code} {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def api() -> TestClient:
    return client


@pytest.fixture(scope="session")
def admin() -> dict:
    """Cabeceras con token de administrador."""
    return _login(ADMIN)


@pytest.fixture(scope="session")
def usuario() -> dict:
    """Cabeceras con token de usuario normal."""
    return _login(USUARIO)
