"""Pruebas de unidad: lógica pura sin base de datos ni llamadas reales de IA."""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from jose import jwt
from pydantic import ValidationError

from app import agente_base, seguridad, tokens
from app.config import JWT_SECRET
from app.herramientas import comparar_con_presupuesto
from app.main import INDEX, app
from app.schemas import AgentePeticion, ChatPregunta, ResenaCrear, UsuarioCrear, VideojuegoCrear


# ----------------------------- Seguridad / JWT -----------------------------

def test_token_se_crea_y_decodifica():
    token = seguridad.crear_token(42, "admin")
    datos = seguridad.decodificar_token(token)
    assert datos is not None
    assert datos["sub"] == "42"
    assert datos["rol"] == "admin"
    assert "exp" in datos


def test_token_basura_es_rechazado():
    assert seguridad.decodificar_token("esto.no.es.un.token") is None
    assert seguridad.decodificar_token("") is None


def test_token_expirado_es_rechazado():
    """La expiración del JWT (8 h) es efectiva: un token vencido da None → 401."""
    vencido = jwt.encode(
        {"sub": "1", "rol": "admin",
         "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        JWT_SECRET, algorithm="HS256",
    )
    assert seguridad.decodificar_token(vencido) is None


def test_password_hash_y_verificacion():
    h = seguridad.hashear_password("Secreto123")
    assert h != "Secreto123"
    assert seguridad.verificar_password("Secreto123", h) is True
    assert seguridad.verificar_password("otra", h) is False


def test_password_hash_corrupto_no_crashea():
    assert seguridad.verificar_password("x", "hash-invalido") is False


# -------------------------- Validaciones de datos --------------------------

def test_email_patron():
    assert UsuarioCrear(nombre="Ana", email="ana@x.com", password="123456")
    with pytest.raises(ValidationError):
        UsuarioCrear(nombre="Ana", email="no-es-correo", password="123456")


def test_rol_invalido_rechazado():
    with pytest.raises(ValidationError):
        UsuarioCrear(nombre="Ana", email="ana@x.com", password="123456", rol="superuser")


def test_precio_negativo_rechazado():
    with pytest.raises(ValidationError):
        VideojuegoCrear(titulo="T", genero="G", plataforma="P", precio=-1)


def test_puntuacion_fuera_de_rango_rechazada():
    with pytest.raises(ValidationError):
        ResenaCrear(videojuego_id=1, autor="X", puntuacion=9)


def test_pregunta_demasiado_larga_rechazada():
    with pytest.raises(ValidationError):
        ChatPregunta(pregunta="x" * 1001)


def test_pregunta_minima():
    with pytest.raises(ValidationError):
        ChatPregunta(pregunta="a")  # mínimo 2 caracteres
    assert ChatPregunta(pregunta="Hola")


def test_solicitud_agente_minima():
    with pytest.raises(ValidationError):
        AgentePeticion(solicitud="a")
    assert AgentePeticion(solicitud="ab")


# ------------------------- Lógica de tokens / cupo -------------------------

def test_cupo_agotado_responde_429(monkeypatch):
    monkeypatch.setattr(tokens, "tokens_consumidos", lambda usuario_id: 100000)
    with pytest.raises(Exception) as err:
        tokens.verificar_cupo({"id": 1, "limite_tokens": 100000})
    assert getattr(err.value, "status_code", None) == 429


def test_cupo_restante_calculado(monkeypatch):
    monkeypatch.setattr(tokens, "tokens_consumidos", lambda usuario_id: 30000)
    assert tokens.verificar_cupo({"id": 1, "limite_tokens": 100000}) == 70000


# ---------------------- Agente de presupuesto (cálculo) ---------------------

def test_comparar_presupuesto_alcanza():
    r = comparar_con_presupuesto({}, total=50, presupuesto=100)
    assert r["alcanza"] is True
    assert r["diferencia"] == 50
    assert r["porcentaje_usado"] == 50.0


def test_comparar_presupuesto_no_alcanza():
    r = comparar_con_presupuesto({}, total=99.97, presupuesto=90)
    assert r["alcanza"] is False
    assert r["diferencia"] == -9.97


def test_comparar_presupuesto_cero_y_no_numerico():
    assert comparar_con_presupuesto({}, total=10, presupuesto=0)["porcentaje_usado"] is None
    assert "error" in comparar_con_presupuesto({}, total="abc", presupuesto=10)


# ------------------- Bucle del agente (IA simulada, sin Groq) ---------------

def _mensaje(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


def _llamada(nombre, argumentos):
    return SimpleNamespace(
        id="tc_1",
        function=SimpleNamespace(name=nombre, arguments=json.dumps(argumentos)),
    )


def _guion(monkeypatch, respuestas):
    """Reemplaza la llamada a Groq por una lista de respuestas guionadas."""
    indice = {"i": 0}

    def falsa_llamada(mensajes, tools=None):
        r = respuestas[indice["i"]]
        indice["i"] += 1
        return r["mensaje"], r["entrada"], r["salida"]

    monkeypatch.setattr(agente_base, "llamar_modelo_tools", falsa_llamada)


def test_bucle_agente_ejecuta_herramienta(monkeypatch):
    _guion(monkeypatch, [
        {"mensaje": _mensaje(tool_calls=[
            _llamada("comparar_con_presupuesto", {"total": 100, "presupuesto": 80})]),
         "entrada": 10, "salida": 5},
        {"mensaje": _mensaje(content="No alcanza: faltan Q20."), "entrada": 12, "salida": 6},
    ])
    r = agente_base.ejecutar_agente("sys", "solicitud", ["comparar_con_presupuesto"], 10000)
    assert len(r["pasos"]) == 1
    assert r["pasos"][0]["herramienta"] == "comparar_con_presupuesto"
    assert r["pasos"][0]["resultado"]["alcanza"] is False
    assert r["respuesta"] == "No alcanza: faltan Q20."
    assert r["t_entrada"] == 22 and r["t_salida"] == 11


def test_bucle_agente_respuesta_directa(monkeypatch):
    _guion(monkeypatch, [
        {"mensaje": _mensaje(content="Respuesta sin herramientas"), "entrada": 8, "salida": 4},
    ])
    r = agente_base.ejecutar_agente("sys", "solicitud", ["buscar_juego"], 10000)
    assert r["pasos"] == []
    assert r["respuesta"] == "Respuesta sin herramientas"


def test_bucle_agente_respeta_tope_de_tokens(monkeypatch):
    _guion(monkeypatch, [
        {"mensaje": _mensaje(tool_calls=[
            _llamada("comparar_con_presupuesto", {"total": 10, "presupuesto": 5})]),
         "entrada": 600, "salida": 0},
    ])
    r = agente_base.ejecutar_agente("sys", "solicitud", ["comparar_con_presupuesto"], 500)
    assert "límite de tokens" in r["respuesta"]


def test_bucle_agente_fuerza_respuesta_final(monkeypatch):
    """Si se agotan los pasos sin terminar, redacta una respuesta final sin herramientas."""
    llamada_herramienta = {"mensaje": _mensaje(tool_calls=[
        _llamada("comparar_con_presupuesto", {"total": 1, "presupuesto": 2})]),
        "entrada": 1, "salida": 1}
    _guion(monkeypatch, [llamada_herramienta.copy() for _ in range(agente_base.MAX_PASOS)] + [
        {"mensaje": _mensaje(content="Resumen final"), "entrada": 3, "salida": 2},
    ])
    r = agente_base.ejecutar_agente("sys", "solicitud", ["comparar_con_presupuesto"], 10000)
    assert r["respuesta"] == "Resumen final"
    assert len(r["pasos"]) == agente_base.MAX_PASOS


# ----------------- Cliente Groq simulado (sin llamadas reales) --------------

def test_llamar_modelo_extrae_tokens(monkeypatch):
    from app import ia
    respuesta = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7),
        choices=[SimpleNamespace(message=_mensaje(content="hola"))],
    )
    cliente = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=lambda **kw: respuesta)))
    monkeypatch.setattr(ia, "_obtener_cliente", lambda: cliente)
    mensaje, entrada, salida = ia.llamar_modelo([{"role": "user", "content": "x"}])
    assert (mensaje.content, entrada, salida) == ("hola", 11, 7)


def test_llamar_modelo_error_responde_502(monkeypatch):
    from app import ia
    from fastapi import HTTPException

    class ClienteFalso:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    raise RuntimeError("groq caído")

    monkeypatch.setattr(ia, "_obtener_cliente", ClienteFalso)
    with pytest.raises(HTTPException) as err:
        ia.llamar_modelo([{"role": "user", "content": "x"}])
    assert err.value.status_code == 502


# ----------------------- Moneda (quetzales) en el código ---------------------

def test_prompts_usan_quetzales():
    from app import agentes, chatbot
    assert "quetzales (Q)" in chatbot.SYSTEM_PROMPT
    assert "USD" not in chatbot.SYSTEM_PROMPT
    assert "quetzales, Q" in agentes.PROMPT_PRESUPUESTO
    assert "USD" not in agentes.PROMPT_PRESUPUESTO


def test_interfaz_web_usa_quetzales():
    html = INDEX.read_text(encoding="utf-8")
    assert "money = n => 'Q'" in html       # formateador de precios en quetzales
    assert "'$' + Number" not in html       # sin símbolo de dólar
    assert "Precio (Q)" in html
    assert "USD" not in html


# -------------------------- Documentación Swagger ---------------------------

def test_openapi_contiene_rutas_principales():
    spec = app.openapi()
    for ruta in ["/auth/login", "/videojuegos", "/resenas", "/ia/chatbot",
                 "/ia/agente-presupuesto", "/ia/agente-alternativas",
                 "/historial/conversaciones", "/consumo/mio",
                 "/reportes/consumo", "/reportes/conversaciones",
                 "/usuarios", "/servicios"]:
        assert ruta in spec["paths"], f"Falta la ruta documentada {ruta}"
    assert "OAuth2PasswordBearer" in spec["components"]["securitySchemes"]
