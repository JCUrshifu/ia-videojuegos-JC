"""Pruebas de los servicios de IA con el modelo SIMULADO.

No se consume cuota de Groq y no se escriben datos en la base de datos
(guardar_intercambio se reemplaza por una función falsa).
La base de datos solo se LEE (búsqueda RAG, servicio activo y cupo).
"""
import pytest

from app import agentes, chatbot
from app.herramientas import calcular_total


def _simular_ia(monkeypatch, respuesta="Respuesta simulada del asistente.",
                entrada=100, salida=20, conversacion_id=999):
    """Reemplaza la llamada a Groq y el guardado en BD por dobles de prueba."""
    def falsa_llamada(mensajes, tools=None, temperature=0.2):
        return type("Mensaje", (), {"content": respuesta, "tool_calls": None})(), entrada, salida

    monkeypatch.setattr("app.ia.llamar_modelo", falsa_llamada)
    monkeypatch.setattr(chatbot, "guardar_intercambio", lambda *a, **k: conversacion_id)


def _agente_falso(monkeypatch, respuesta="Recomendación simulada.", pasos=None,
                   fuentes=None, entrada=500, salida=100):
    resultado = {
        "respuesta": respuesta,
        "pasos": pasos if pasos is not None else [],
        "fuentes": fuentes if fuentes is not None else [],
        "t_entrada": entrada,
        "t_salida": salida,
    }
    monkeypatch.setattr(agentes.agente_base, "ejecutar_agente",
                        lambda *a, **k: dict(resultado))
    monkeypatch.setattr(chatbot, "guardar_intercambio", lambda *a, **k: 999)


# ------------------------------ Chatbot RAG ---------------------------------

def test_chatbot_respuesta_simulada(api, admin, monkeypatch):
    _simular_ia(monkeypatch, respuesta="Mario Kart 8 [ID 12].")
    r = api.post("/ia/chatbot",
                 json={"pregunta": "¿Qué juegos de carreras tienes?"},
                 headers=admin)
    assert r.status_code == 200
    datos = r.json()
    assert datos["respuesta"] == "Mario Kart 8 [ID 12]."
    assert datos["conversacion_id"] == 999            # no se escribió nada en la BD
    assert datos["tokens"] == {"entrada": 100, "salida": 20, "total": 120}
    assert datos["tokens_restantes"] >= 0
    assert isinstance(datos["informacion_suficiente"], bool)
    assert isinstance(datos["fuentes"], list)
    for f in datos["fuentes"]:
        assert {"id", "titulo"} <= set(f)


def test_chatbot_conversacion_inexistente_404(api, admin):
    """Se responde 404 ANTES de llamar al modelo (no se gasta IA)."""
    r = api.post("/ia/chatbot",
                 json={"pregunta": "hola", "conversacion_id": 999999},
                 headers=admin)
    assert r.status_code == 404


def test_chatbot_pregunta_larga_422(api, admin):
    r = api.post("/ia/chatbot", json={"pregunta": "x" * 1001}, headers=admin)
    assert r.status_code == 422


def test_chatbot_pregunta_vacia_422(api, admin):
    r = api.post("/ia/chatbot", json={"pregunta": "a"}, headers=admin)
    assert r.status_code == 422


# --------------------------- Agentes de IA ----------------------------------

@pytest.mark.parametrize("ruta", ["/ia/agente-presupuesto", "/ia/agente-alternativas"])
def test_agente_respuesta_simulada(api, admin, monkeypatch, ruta):
    _agente_falso(
        monkeypatch,
        respuesta="Todo correcto.",
        pasos=[{"paso": 1, "herramienta": "buscar_juego",
                "argumentos": {"busqueda": "Elden Ring"},
                "resultado": {"encontrados": 1}}],
        fuentes=[{"tipo": "catalogo", "id": 2, "titulo": "Elden Ring"}],
    )
    r = api.post(ruta, json={"solicitud": "Quiero Elden Ring, tengo Q100."}, headers=admin)
    assert r.status_code == 200
    datos = r.json()
    assert datos["respuesta"] == "Todo correcto."
    assert datos["conversacion_id"] == 999
    assert len(datos["pasos"]) == 1
    assert datos["pasos"][0]["herramienta"] == "buscar_juego"
    assert datos["fuentes"][0]["titulo"] == "Elden Ring"
    assert datos["tokens"] == {"entrada": 500, "salida": 100, "total": 600}
    assert datos["tokens_restantes"] >= 0


def test_agente_solicitud_corta_422(api, admin):
    r = api.post("/ia/agente-presupuesto", json={"solicitud": "a"}, headers=admin)
    assert r.status_code == 422


# ------------------- Herramientas contra la base de datos ---------------------

def test_herramienta_calcular_total(api, admin):
    """Suma los precios REALES de la BD (solo lectura)."""
    ctx = {"fuentes": []}
    r = calcular_total(ctx, ids=[2, 5, 6])
    assert r.get("ids_no_encontrados") == []
    assert len(r["juegos"]) == 3
    assert r["total"] > 0
    assert len(ctx["fuentes"]) == 3
