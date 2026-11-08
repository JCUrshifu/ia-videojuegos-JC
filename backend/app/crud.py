from fastapi import HTTPException
from psycopg2 import errors

from app.db import get_cursor


def actualizar_fila(tabla: str, id_: int, campos: dict, permitidas: set, retorno: str) -> dict:
    """UPDATE genérico: solo toca las columnas permitidas que vengan en `campos`."""
    if not campos:
        raise HTTPException(status_code=400, detail="No se envió ningún campo para actualizar")
    for columna in campos:
        if columna not in permitidas:
            raise HTTPException(status_code=400, detail=f"Campo no permitido: {columna}")
    asignaciones = ", ".join(f"{columna} = %s" for columna in campos)
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                f"UPDATE {tabla} SET {asignaciones} WHERE id = %s RETURNING {retorno}",
                (*campos.values(), id_),
            )
            fila = cur.fetchone()
    except errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Ya existe un registro con ese valor único")
    if not fila:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return fila