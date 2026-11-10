"""Pruebas de roles y permisos: el usuario normal no puede escribir ni ver datos ajenos.

Todas las peticiones de escritura están DENEGADAS (403/401), por lo que
no se crea ni se borra ningún dato real.
"""
import pytest

from tests.conftest import requiere_bd


# ------------------------- Sin token (401) ----------------------------------

@pytest.mark.parametrize("metodo, ruta, cuerpo", [
    ("GET", "/usuarios", None),
    ("GET", "/reportes/consumo", None),
    ("GET", "/historial/conversaciones", None),
    ("POST", "/ia/chatbot", {"pregunta": "hola"}),
    ("POST", "/videojuegos", {"titulo": "T", "genero": "G", "plataforma": "P", "precio": 1}),
    ("DELETE", "/videojuegos/1", None),
])
def test_sin_token_responde_401(api, metodo, ruta, cuerpo):
    opciones = {}
    if cuerpo is not None:
        opciones["json"] = cuerpo
    r = api.request(metodo, ruta, **opciones)
    assert r.status_code == 401


# ------------------- Usuario normal intenta escribir (403) -------------------

@pytest.mark.parametrize("metodo, ruta, cuerpo", [
    ("POST", "/usuarios", {"nombre": "X", "email": "x@x.com", "password": "123456"}),
    ("PUT", "/usuarios/1", {"limite_tokens": 1}),
    ("DELETE", "/usuarios/1", None),
    ("PUT", "/servicios/1", {"activo": False}),
    ("POST", "/videojuegos", {"titulo": "T", "genero": "G", "plataforma": "P", "precio": 1}),
    ("PUT", "/videojuegos/1", {"stock": 99}),
    ("DELETE", "/videojuegos/1", None),
    ("POST", "/resenas", {"videojuego_id": 1, "autor": "T", "puntuacion": 5}),
    ("DELETE", "/resenas/1", None),
])
def test_usuario_no_puede_escribir(api, usuario, metodo, ruta, cuerpo):
    opciones = {"headers": usuario}
    if cuerpo is not None:
        opciones["json"] = cuerpo
    r = api.request(metodo, ruta, **opciones)
    assert r.status_code == 403
    assert "administrador" in r.json()["detail"].lower()


def test_usuario_no_puede_ver_otro_usuario(api, admin, usuario):
    r_me = api.get("/auth/me", headers=admin)
    admin_id = r_me.json()["id"]
    r = api.get("/reportes/consumo", params={"usuario_id": admin_id}, headers=usuario)
    assert r.status_code == 403
    assert "propio" in r.json()["detail"].lower()


# ----------------- Aislamiento de conversaciones entre usuarios --------------

def test_usuario_no_abre_conversacion_ajena(api, admin, usuario):
    requiere_bd()
    lista = api.get("/reportes/conversaciones", headers=admin).json()
    # una conversación que NO pertenezca al usuario normal (las del admin sirven)
    r_me = api.get("/auth/me", headers=usuario)
    usuario_id = r_me.json()["id"]
    ajena = next((c for c in lista if c["usuario_id"] != usuario_id), None)
    if ajena is None:
        pytest.skip("Aún no hay conversaciones ajenas en esta base de datos")
    # el admin sí puede abrirla
    assert api.get(f"/reportes/conversaciones/{ajena['id']}", headers=admin).status_code == 200
    # el usuario normal no
    assert api.get(f"/reportes/conversaciones/{ajena['id']}", headers=usuario).status_code == 404
    assert api.get(f"/historial/conversaciones/{ajena['id']}", headers=usuario).status_code == 404


def test_conversacion_inexistente_404(api, admin):
    assert api.get("/reportes/conversaciones/999999", headers=admin).status_code == 404
    assert api.get("/historial/conversaciones/999999", headers=admin).status_code == 404


def test_perfil_usuario_normal(api, usuario):
    r = api.get("/auth/me", headers=usuario)
    assert r.status_code == 200
    assert r.json()["rol"] == "usuario"
