from fastapi import APIRouter, Depends, HTTPException

from app.db import get_cursor
from app.deps import usuario_actual
from app.tokens import tokens_consumidos

historial = APIRouter(prefix="/historial", tags=["Historial"])
consumo = APIRouter(prefix="/consumo", tags=["Consumo de tokens"])


@historial.get("/conversaciones")
def mis_conversaciones(usuario: dict = Depends(usuario_actual)):
    """Lista las conversaciones del usuario que inició sesión."""
    with get_cursor() as cur:
        cur.execute(
            """SELECT c.id, s.codigo AS servicio, s.nombre AS servicio_nombre, c.titulo, c.creado_en,
                      (SELECT COUNT(*) FROM mensajes m WHERE m.conversacion_id = c.id) AS mensajes,
                      COALESCE((SELECT SUM(t.tokens_total) FROM consumo_tokens t
                                WHERE t.conversacion_id = c.id), 0) AS tokens
               FROM conversaciones c
               JOIN servicios s ON s.id = c.servicio_id
               WHERE c.usuario_id = %s
               ORDER BY c.id DESC""",
            (usuario["id"],),
        )
        return cur.fetchall()


@historial.get("/conversaciones/{conversacion_id}")
def ver_conversacion(conversacion_id: int, usuario: dict = Depends(usuario_actual)):
    """Mensajes de una conversación (solo si es del usuario)."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, titulo, creado_en FROM conversaciones WHERE id = %s AND usuario_id = %s",
            (conversacion_id, usuario["id"]),
        )
        conversacion = cur.fetchone()
        if not conversacion:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        cur.execute(
            "SELECT id, rol, contenido, fuentes, creado_en FROM mensajes WHERE conversacion_id = %s ORDER BY id",
            (conversacion_id,),
        )
        conversacion["mensajes"] = cur.fetchall()
    return conversacion


@consumo.get("/mio")
def mi_consumo(usuario: dict = Depends(usuario_actual)):
    """Límite, consumo acumulado y desglose por servicio del usuario."""
    consumido = tokens_consumidos(usuario["id"])
    with get_cursor() as cur:
        cur.execute(
            """SELECT s.codigo AS servicio, s.nombre AS servicio_nombre,
                      COUNT(*) AS consultas, SUM(t.tokens_total) AS tokens
               FROM consumo_tokens t
               JOIN servicios s ON s.id = t.servicio_id
               WHERE t.usuario_id = %s
               GROUP BY s.codigo, s.nombre
               ORDER BY s.codigo""",
            (usuario["id"],),
        )
        por_servicio = cur.fetchall()
    return {
        "limite": usuario["limite_tokens"],
        "consumido": consumido,
        "restante": max(usuario["limite_tokens"] - consumido, 0),
        "por_servicio": por_servicio,
    }