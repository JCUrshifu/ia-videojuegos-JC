from fastapi import HTTPException
from psycopg2.extras import Json

from app import ia, rag, tokens
from app.db import get_cursor

CODIGO_SERVICIO = "chatbot_rag"
MAX_HISTORIAL = 10

SYSTEM_PROMPT = """Eres el asistente de una tienda de videojuegos. Respondes siempre en español, de forma clara y breve.
Reglas:
1. Usa ÚNICAMENTE la información de la sección CONTEXTO (datos de la base de datos). No inventes juegos, precios ni datos.
2. Cuando uses un juego del contexto, menciónalo por su título y cita la fuente con el formato [ID n].
3. Si el CONTEXTO no tiene información suficiente para responder, di exactamente: "No tengo información suficiente en el catálogo para responder eso." y sugiere reformular la pregunta.
4. Los precios están en quetzales (Q).
5. Usa el historial de la conversación para entender preguntas de seguimiento."""


def cargar_historial(conversacion_id: int, usuario_id: int, servicio_id: int) -> list:
    """Verifica que la conversación sea del usuario y devuelve los últimos mensajes."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id FROM conversaciones WHERE id = %s AND usuario_id = %s AND servicio_id = %s",
            (conversacion_id, usuario_id, servicio_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        cur.execute(
            """SELECT rol, contenido FROM (
                   SELECT id, rol, contenido FROM mensajes
                   WHERE conversacion_id = %s ORDER BY id DESC LIMIT %s
               ) ultimos ORDER BY id""",
            (conversacion_id, MAX_HISTORIAL),
        )
        filas = cur.fetchall()
    return [
        {"role": "user" if f["rol"] == "usuario" else "assistant", "content": f["contenido"]}
        for f in filas
    ]


def guardar_intercambio(usuario_id, servicio_id, conversacion_id, pregunta, respuesta,
                        fuentes, t_entrada, t_salida) -> int:
    """Guarda conversación (si es nueva), mensajes y consumo en una sola transacción."""
    with get_cursor(commit=True) as cur:
        if conversacion_id is None:
            cur.execute(
                "INSERT INTO conversaciones (usuario_id, servicio_id, titulo) VALUES (%s, %s, %s) RETURNING id",
                (usuario_id, servicio_id, pregunta[:80]),
            )
            conversacion_id = cur.fetchone()["id"]
        cur.execute(
            "INSERT INTO mensajes (conversacion_id, rol, contenido) VALUES (%s, 'usuario', %s)",
            (conversacion_id, pregunta),
        )
        cur.execute(
            "INSERT INTO mensajes (conversacion_id, rol, contenido, fuentes) VALUES (%s, 'asistente', %s, %s)",
            (conversacion_id, respuesta, Json(fuentes)),
        )
        tokens.registrar_consumo(cur, usuario_id, servicio_id, conversacion_id, t_entrada, t_salida)
    return conversacion_id


def responder(usuario: dict, pregunta: str, conversacion_id: int | None = None) -> dict:
    servicio = tokens.obtener_servicio_activo(CODIGO_SERVICIO)   # 403 si está desactivado
    restante = tokens.verificar_cupo(usuario)                     # 429 si agotó su límite

    historial = []
    if conversacion_id is not None:
        historial = cargar_historial(conversacion_id, usuario["id"], servicio["id"])

    # En preguntas de seguimiento, la búsqueda usa también la pregunta anterior.
    texto_busqueda = pregunta
    previas = [m["content"] for m in historial if m["role"] == "user"]
    if previas:
        texto_busqueda = previas[-1] + " " + pregunta

    juegos = rag.recuperar_juegos(texto_busqueda)
    contexto = rag.construir_contexto(juegos)

    mensajes = [{"role": "system", "content": SYSTEM_PROMPT}]
    mensajes += historial
    mensajes.append({"role": "user", "content": f"CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}"})

    mensaje_ia, t_entrada, t_salida = ia.llamar_modelo(mensajes)
    respuesta = (mensaje_ia.content or "").strip() or "No pude generar una respuesta. Intenta de nuevo."

    fuentes = [{"id": j["id"], "titulo": j["titulo"]} for j in juegos]
    conversacion_id = guardar_intercambio(
        usuario["id"], servicio["id"], conversacion_id, pregunta, respuesta,
        fuentes, t_entrada, t_salida,
    )
    total = t_entrada + t_salida
    return {
        "conversacion_id": conversacion_id,
        "respuesta": respuesta,
        "fuentes": fuentes,
        "informacion_suficiente": bool(juegos),
        "tokens": {"entrada": t_entrada, "salida": t_salida, "total": total},
        "tokens_restantes": max(restante - total, 0),
    }