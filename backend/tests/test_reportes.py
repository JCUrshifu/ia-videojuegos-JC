"""Pruebas de historial, consumo de tokens y reportes (Componente 4).

Solo LECTURA: validan coherencia, filtros por servicio/fecha y aislamiento.
"""
from datetime import date, timedelta

from tests.conftest import requiere_bd


# ------------------------- Reporte de consumo (admin) ------------------------

def test_consumo_coherencia_interna(api, admin):
    r = api.get("/reportes/consumo", headers=admin)
    assert r.status_code == 200
    datos = r.json()
    totales = datos["totales"]

    suma_servicio = sum(s["consultas"] for s in datos["por_servicio"])
    suma_servicio_tokens = sum(s["tokens_total"] for s in datos["por_servicio"])
    suma_usuario = sum(u["consultas"] for u in datos["por_usuario"])

    assert suma_servicio == totales["consultas"]
    assert suma_servicio_tokens == totales["tokens_total"]
    assert suma_usuario == totales["consultas"]
    assert totales["tokens_total"] == totales["tokens_entrada"] + totales["tokens_salida"]


def test_consumo_por_dia_acumulado(api, admin):
    datos = api.get("/reportes/consumo", headers=admin).json()
    acumulado = 0
    for fila in datos["por_dia"]:
        acumulado += fila["tokens_total"]
        assert fila["tokens_acumulado"] == acumulado


def test_consumo_filtro_por_servicio(api, admin):
    r = api.get("/reportes/consumo", params={"servicio": "chatbot_rag"}, headers=admin)
    assert r.status_code == 200
    datos = r.json()
    assert datos["filtros"]["servicio"] == "chatbot_rag"
    for fila in datos["por_servicio"]:
        assert fila["servicio"] == "chatbot_rag"


def test_consumo_fechas_invalidas_400(api, admin):
    r = api.get("/reportes/consumo",
                params={"desde": "2026-12-31", "hasta": "2026-01-01"},
                headers=admin)
    assert r.status_code == 400


def test_consumo_filtro_fecha_futura_vacio(api, admin):
    datos = api.get("/reportes/consumo",
                    params={"desde": "2030-01-01", "hasta": "2030-01-05"},
                    headers=admin).json()
    assert datos["totales"]["consultas"] == 0
    assert datos["por_servicio"] == []
    assert datos["por_dia"] == []


def test_detalle_formato_plano(api, admin):
    """Formato 'una fila por consulta', el que consume Power BI."""
    r = api.get("/reportes/detalle", headers=admin)
    assert r.status_code == 200
    filas = r.json()
    assert isinstance(filas, list)
    if filas:
        assert {"id", "fecha", "dia", "usuario", "servicio",
                "tokens_total"} <= set(filas[0])


# ------------------------- Aislamiento por usuario ---------------------------

def test_usuario_normal_solo_ve_sus_datos(api, usuario):
    r_me = api.get("/auth/me", headers=usuario)
    mi_id = r_me.json()["id"]
    # el reporte se acota solo, aunque no se pida usuario_id
    datos = api.get("/reportes/consumo", headers=usuario).json()
    assert datos["filtros"]["usuario_id"] == mi_id
    for fila in datos["por_usuario"]:
        assert fila["usuario_id"] == mi_id


def test_conversaciones_solo_propias(api, usuario):
    mi_id = api.get("/auth/me", headers=usuario).json()["id"]
    lista = api.get("/reportes/conversaciones", headers=usuario).json()
    assert all(c["usuario_id"] == mi_id for c in lista)


def test_admin_ve_conversaciones_de_todos(api, admin):
    lista = api.get("/reportes/conversaciones", headers=admin).json()
    assert isinstance(lista, list)
    if lista:
        assert {"id", "titulo", "usuario_id", "servicio", "mensajes", "tokens"} <= set(lista[0])


# ------------------------------ Historial ------------------------------------

def test_historial_del_usuario(api, usuario):
    r = api.get("/historial/conversaciones", headers=usuario)
    assert r.status_code == 200
    for c in r.json():
        assert {"id", "servicio", "titulo", "mensajes", "tokens"} <= set(c)


def test_historial_detalle(api, admin):
    lista = api.get("/historial/conversaciones", headers=admin).json()
    if not lista:
        return  # base de datos recién creada: no hay nada que abrir
    detalle = api.get(f"/historial/conversaciones/{lista[0]['id']}", headers=admin)
    assert detalle.status_code == 200
    datos = detalle.json()
    assert isinstance(datos["mensajes"], list)
    for m in datos["mensajes"]:
        assert m["rol"] in ("usuario", "asistente")


# --------------------------- Mi consumo de tokens ----------------------------

def test_mi_consumo(api, usuario):
    r = api.get("/consumo/mio", headers=usuario)
    assert r.status_code == 200
    datos = r.json()
    assert datos["consumido"] <= datos["limite"] or datos["restante"] == 0
    assert datos["restante"] == max(datos["limite"] - datos["consumido"], 0)
    suma = sum(s["tokens"] or 0 for s in datos["por_servicio"])
    assert suma == datos["consumido"]


def test_ver_conversacion_no_existente(api, admin):
    assert api.get("/historial/conversaciones/999999", headers=admin).status_code == 404
