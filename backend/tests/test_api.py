"""Pruebas de integración del API REST: sistema, autenticación y catálogo.

Todas son de LECTURA: no crean ni modifican datos.
"""
from tests.conftest import requiere_bd


# ------------------------------- Sistema ------------------------------------

def test_health_check(api):
    r = api.get("/health")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok"}


def test_salud_reporta_bd(api):
    requiere_bd()
    r = api.get("/salud")
    assert r.status_code == 200
    datos = r.json()
    assert datos["estado"] == "ok"
    assert datos["videojuegos"] >= 40
    assert datos["servicios"] >= 3


# ---------------------------- Autenticación ---------------------------------

def test_login_admin(api):
    requiere_bd()
    r = api.post("/auth/login", data={"username": "admin@videojuegos.com", "password": "Admin123"})
    assert r.status_code == 200
    datos = r.json()
    assert datos["token_type"] == "bearer"
    assert datos["rol"] == "admin"
    assert len(datos["access_token"]) > 20


def test_login_contrasena_incorrecta(api):
    requiere_bd()
    r = api.post("/auth/login", data={"username": "admin@videojuegos.com", "password": "mala"})
    assert r.status_code == 401


def test_login_usuario_inexistente(api):
    requiere_bd()
    r = api.post("/auth/login", data={"username": "nadie@videojuegos.com", "password": "x123456"})
    assert r.status_code == 401


def test_perfil_me(api, admin):
    r = api.get("/auth/me", headers=admin)
    assert r.status_code == 200
    datos = r.json()
    assert datos["rol"] == "admin"
    assert datos["email"] == "admin@videojuegos.com"
    assert "password_hash" not in datos  # nunca expone el hash


def test_logout_sin_estado(api, admin):
    r = api.post("/auth/logout", headers=admin)
    assert r.status_code == 200
    assert "token" in r.json()["mensaje"].lower()


# ------------------------------- Catálogo -----------------------------------

def test_catalogo_requiere_token(api):
    r = api.get("/videojuegos")
    assert r.status_code == 401


def test_catalogo_lista(api, admin):
    r = api.get("/videojuegos", headers=admin)
    assert r.status_code == 200
    juegos = r.json()
    assert isinstance(juegos, list)
    assert len(juegos) >= 40
    assert {"id", "titulo", "genero", "plataforma", "precio", "stock"} <= set(juegos[0])


def test_catalogo_busqueda_q(api, admin):
    r = api.get("/videojuegos", params={"q": "zelda"}, headers=admin)
    assert r.status_code == 200
    assert any("zelda" in j["titulo"].lower() for j in r.json())


def test_catalogo_filtro_genero(api, admin):
    r = api.get("/videojuegos", params={"genero": "Acción"}, headers=admin)
    assert r.status_code == 200
    assert all(j["genero"].lower() == "acción" for j in r.json())


def test_catalogo_filtro_precio_maximo(api, admin):
    r = api.get("/videojuegos", params={"precio_max": 10}, headers=admin)
    assert r.status_code == 200
    assert all(float(j["precio"]) <= 10 for j in r.json())


def test_catalogo_inyeccion_sql_no_rompe(api, admin):
    """Un intento de inyección se trata como texto: la consulta no falla y la tabla sigue intacta."""
    r = api.get("/videojuegos", params={"q": "'; DROP TABLE videojuegos;--"}, headers=admin)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    salud = api.get("/salud").json()
    assert salud["videojuegos"] >= 40  # la tabla sobrevivió


def test_videojuego_inexistente_404(api, admin):
    assert api.get("/videojuegos/999999", headers=admin).status_code == 404


def test_videojuego_id_no_numerico_422(api, admin):
    assert api.get("/videojuegos/abc", headers=admin).status_code == 422


def test_resenas_por_juego(api, admin):
    r = api.get("/resenas", params={"videojuego_id": 1}, headers=admin)
    assert r.status_code == 200
    assert all(x["videojuego_id"] == 1 for x in r.json())


def test_servicios_activos(api, admin):
    r = api.get("/servicios", headers=admin)
    assert r.status_code == 200
    servicios = r.json()
    assert len(servicios) >= 3
    codigos = {s["codigo"] for s in servicios}
    assert {"chatbot_rag", "agente_presupuesto", "agente_alternativas"} <= codigos
