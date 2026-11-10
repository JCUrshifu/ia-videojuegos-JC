from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_cursor
from app.deps import usuario_actual

router = APIRouter(prefix="/reportes", tags=["Reportes y uso"])

ZONA = "America/Guatemala"

FROM_CONSUMO = """FROM consumo_tokens t
                  JOIN servicios s ON s.id = t.servicio_id
                  JOIN usuarios u ON u.id = t.usuario_id"""

FROM_CONVERSACIONES = """FROM conversaciones c
                         JOIN servicios s ON s.id = c.servicio_id
                         JOIN usuarios u ON u.id = c.usuario_id"""


def _dia(alias: str) -> str:
    """Fecha (día) en hora de Guatemala de la columna creado_en."""
    return f"({alias}.creado_en AT TIME ZONE '{ZONA}')::date"


def _filtros(usuario: dict, usuario_id, servicio, desde, hasta, alias: str):
    """Arma el WHERE. Un usuario normal solo puede ver sus propios datos."""
    if desde and hasta and desde > hasta:
        raise HTTPException(status_code=400, detail="'desde' no puede ser posterior a 'hasta'")
    if usuario["rol"] != "admin":
        if usuario_id is not None and usuario_id != usuario["id"]:
            raise HTTPException(status_code=403, detail="Solo puedes consultar tu propio consumo")
        usuario_id = usuario["id"]

    condiciones, valores = [], []
    if usuario_id is not None:
        condiciones.append(f"{alias}.usuario_id = %s")
        valores.append(usuario_id)
    if servicio:
        condiciones.append("s.codigo = %s")
        valores.append(servicio)
    if desde:
        condiciones.append(f"{_dia(alias)} >= %s")
        valores.append(desde)
    if hasta:
        condiciones.append(f"{_dia(alias)} <= %s")
        valores.append(hasta)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    return donde, valores, usuario_id


@router.get("/consumo")
def reporte_consumo(
    usuario_id: Optional[int] = Query(None, description="Solo admin: filtra por usuario"),
    servicio: Optional[str] = Query(None, description="Código: chatbot_rag, agente_presupuesto o agente_alternativas"),
    desde: Optional[date] = Query(None, description="Fecha inicial (AAAA-MM-DD), inclusive"),
    hasta: Optional[date] = Query(None, description="Fecha final (AAAA-MM-DD), inclusive"),
    usuario: dict = Depends(usuario_actual),
):
    """Resumen de consultas y tokens: totales, por servicio, por usuario y por día (con acumulado)."""
    donde, valores, usuario_id = _filtros(usuario, usuario_id, servicio, desde, hasta, "t")
    with get_cursor() as cur:
        cur.execute(
            f"""SELECT COUNT(*) AS consultas,
                       COALESCE(SUM(t.tokens_entrada), 0)::bigint AS tokens_entrada,
                       COALESCE(SUM(t.tokens_salida), 0)::bigint AS tokens_salida,
                       COALESCE(SUM(t.tokens_total), 0)::bigint AS tokens_total
                {FROM_CONSUMO} {donde}""",
            valores,
        )
        totales = cur.fetchone()

        cur.execute(
            f"""SELECT s.codigo AS servicio, s.nombre AS servicio_nombre,
                       COUNT(*) AS consultas,
                       SUM(t.tokens_entrada)::bigint AS tokens_entrada,
                       SUM(t.tokens_salida)::bigint AS tokens_salida,
                       SUM(t.tokens_total)::bigint AS tokens_total
                {FROM_CONSUMO} {donde}
                GROUP BY s.codigo, s.nombre
                ORDER BY s.codigo""",
            valores,
        )
        por_servicio = cur.fetchall()

        cur.execute(
            f"""SELECT u.id AS usuario_id, u.nombre AS usuario, u.limite_tokens,
                       COUNT(*) AS consultas,
                       SUM(t.tokens_total)::bigint AS tokens_total
                {FROM_CONSUMO} {donde}
                GROUP BY u.id, u.nombre, u.limite_tokens
                ORDER BY u.id""",
            valores,
        )
        por_usuario = cur.fetchall()

        cur.execute(
            f"""SELECT dia, consultas, tokens_total,
                       SUM(tokens_total) OVER (ORDER BY dia)::bigint AS tokens_acumulado
                FROM (
                    SELECT {_dia('t')} AS dia,
                           COUNT(*) AS consultas,
                           SUM(t.tokens_total)::bigint AS tokens_total
                    {FROM_CONSUMO} {donde}
                    GROUP BY 1
                ) d
                ORDER BY dia""",
            valores,
        )
        por_dia = cur.fetchall()

    return {
        "filtros": {"usuario_id": usuario_id, "servicio": servicio, "desde": desde, "hasta": hasta},
        "totales": totales,
        "por_servicio": por_servicio,
        "por_usuario": por_usuario,
        "por_dia": por_dia,
    }


@router.get("/detalle")
def reporte_detalle(
    usuario_id: Optional[int] = Query(None, description="Solo admin: filtra por usuario"),
    servicio: Optional[str] = Query(None, description="Código del servicio"),
    desde: Optional[date] = Query(None, description="Fecha inicial (AAAA-MM-DD), inclusive"),
    hasta: Optional[date] = Query(None, description="Fecha final (AAAA-MM-DD), inclusive"),
    limite: int = Query(500, ge=1, le=5000, description="Máximo de filas a devolver"),
    usuario: dict = Depends(usuario_actual),
):
    """Una fila por consulta realizada (formato plano, ideal para tablas y para Power BI)."""
    donde, valores, _ = _filtros(usuario, usuario_id, servicio, desde, hasta, "t")
    with get_cursor() as cur:
        cur.execute(
            f"""SELECT t.id,
                       (t.creado_en AT TIME ZONE '{ZONA}') AS fecha,
                       {_dia('t')} AS dia,
                       u.id AS usuario_id, u.nombre AS usuario,
                       s.codigo AS servicio, s.nombre AS servicio_nombre,
                       t.tokens_entrada, t.tokens_salida, t.tokens_total,
                       t.conversacion_id
                {FROM_CONSUMO} {donde}
                ORDER BY t.id DESC
                LIMIT %s""",
            valores + [limite],
        )
        return cur.fetchall()


@router.get("/conversaciones")
def reporte_conversaciones(
    usuario_id: Optional[int] = Query(None, description="Solo admin: filtra por usuario"),
    servicio: Optional[str] = Query(None, description="Código del servicio"),
    desde: Optional[date] = Query(None, description="Fecha inicial (AAAA-MM-DD), inclusive"),
    hasta: Optional[date] = Query(None, description="Fecha final (AAAA-MM-DD), inclusive"),
    limite: int = Query(200, ge=1, le=1000),
    usuario: dict = Depends(usuario_actual),
):
    """Conversaciones guardadas. El admin ve las de todos (con filtros); el usuario, solo las suyas."""
    donde, valores, _ = _filtros(usuario, usuario_id, servicio, desde, hasta, "c")
    with get_cursor() as cur:
        cur.execute(
            f"""SELECT c.id, c.titulo,
                       u.id AS usuario_id, u.nombre AS usuario,
                       s.codigo AS servicio, s.nombre AS servicio_nombre,
                       (c.creado_en AT TIME ZONE '{ZONA}') AS fecha,
                       (SELECT COUNT(*) FROM mensajes m WHERE m.conversacion_id = c.id) AS mensajes,
                       COALESCE((SELECT SUM(k.tokens_total) FROM consumo_tokens k
                                 WHERE k.conversacion_id = c.id), 0)::bigint AS tokens
                {FROM_CONVERSACIONES} {donde}
                ORDER BY c.id DESC
                LIMIT %s""",
            valores + [limite],
        )
        return cur.fetchall()


@router.get("/conversaciones/{conversacion_id}")
def ver_conversacion(conversacion_id: int, usuario: dict = Depends(usuario_actual)):
    """Mensajes de una conversación. El usuario solo puede abrir las suyas; el admin, cualquiera."""
    with get_cursor() as cur:
        cur.execute(
            f"""SELECT c.id, c.titulo, c.usuario_id, u.nombre AS usuario,
                       s.codigo AS servicio, c.creado_en
                {FROM_CONVERSACIONES}
                WHERE c.id = %s""",
            (conversacion_id,),
        )
        conversacion = cur.fetchone()
        if not conversacion or (
            usuario["rol"] != "admin" and conversacion["usuario_id"] != usuario["id"]
        ):
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        cur.execute(
            """SELECT id, rol, contenido, fuentes, creado_en
               FROM mensajes WHERE conversacion_id = %s ORDER BY id""",
            (conversacion_id,),
        )
        conversacion["mensajes"] = cur.fetchall()
    return conversacion