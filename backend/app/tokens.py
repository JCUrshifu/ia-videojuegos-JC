from fastapi import HTTPException

from app.db import get_cursor


def obtener_servicio_activo(codigo: str) -> dict:
    """Devuelve el servicio o responde 404 (no existe) / 403 (desactivado por el admin)."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, codigo, nombre, activo FROM servicios WHERE codigo = %s", (codigo,)
        )
        servicio = cur.fetchone()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    if not servicio["activo"]:
        raise HTTPException(status_code=403, detail="Este servicio está desactivado por el administrador")
    return servicio


def tokens_consumidos(usuario_id: int) -> int:
    with get_cursor() as cur:
        cur.execute(
            "SELECT COALESCE(SUM(tokens_total), 0) AS total FROM consumo_tokens WHERE usuario_id = %s",
            (usuario_id,),
        )
        return int(cur.fetchone()["total"])


def verificar_cupo(usuario: dict) -> int:
    """Bloquea (429) si el usuario ya alcanzó su límite. Devuelve los tokens restantes."""
    consumidos = tokens_consumidos(usuario["id"])
    limite = usuario["limite_tokens"]
    if consumidos >= limite:
        raise HTTPException(
            status_code=429,
            detail=f"Límite de tokens alcanzado ({consumidos} de {limite}). "
                   "Pide al administrador que amplíe tu límite.",
        )
    return limite - consumidos


def registrar_consumo(cur, usuario_id, servicio_id, conversacion_id, tokens_entrada, tokens_salida):
    """Guarda el consumo usando el cursor recibido (misma transacción que los mensajes)."""
    cur.execute(
        """INSERT INTO consumo_tokens
           (usuario_id, servicio_id, conversacion_id, tokens_entrada, tokens_salida, tokens_total)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (usuario_id, servicio_id, conversacion_id,
         tokens_entrada, tokens_salida, tokens_entrada + tokens_salida),
    )