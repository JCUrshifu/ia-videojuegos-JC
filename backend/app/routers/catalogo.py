from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from psycopg2 import errors

from app.crud import actualizar_fila
from app.db import get_cursor
from app.deps import solo_admin, usuario_actual
from app.schemas import ResenaActualizar, ResenaCrear, VideojuegoActualizar, VideojuegoCrear

videojuegos = APIRouter(prefix="/videojuegos", tags=["Videojuegos"])
resenas = APIRouter(prefix="/resenas", tags=["Reseñas"])

COL_JUEGO = "id, titulo, genero, plataforma, precio, stock, anio, descripcion"
PERM_JUEGO = {"titulo", "genero", "plataforma", "precio", "stock", "anio", "descripcion"}
COL_RESENA = "id, videojuego_id, autor, puntuacion, comentario, creado_en"
PERM_RESENA = {"autor", "puntuacion", "comentario"}


# ---------- Videojuegos ----------
@videojuegos.get("")
def listar_juegos(
    q: Optional[str] = None,
    genero: Optional[str] = None,
    precio_max: Optional[float] = None,
    usuario: dict = Depends(usuario_actual),
):
    """Lista el catálogo. Filtros opcionales: título (q), género y precio máximo."""
    condiciones, valores = [], []
    if q:
        condiciones.append("titulo ILIKE %s")
        valores.append(f"%{q}%")
    if genero:
        condiciones.append("genero ILIKE %s")
        valores.append(genero)
    if precio_max is not None:
        condiciones.append("precio <= %s")
        valores.append(precio_max)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    with get_cursor() as cur:
        cur.execute(f"SELECT {COL_JUEGO} FROM videojuegos {donde} ORDER BY titulo", valores)
        return cur.fetchall()


@videojuegos.get("/{juego_id}")
def obtener_juego(juego_id: int, usuario: dict = Depends(usuario_actual)):
    with get_cursor() as cur:
        cur.execute(f"SELECT {COL_JUEGO} FROM videojuegos WHERE id = %s", (juego_id,))
        juego = cur.fetchone()
        if not juego:
            raise HTTPException(status_code=404, detail="Videojuego no encontrado")
        cur.execute(f"SELECT {COL_RESENA} FROM resenas WHERE videojuego_id = %s ORDER BY id", (juego_id,))
        juego["resenas"] = cur.fetchall()
    return juego


@videojuegos.post("", status_code=201)
def crear_juego(datos: VideojuegoCrear, admin: dict = Depends(solo_admin)):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                f"""INSERT INTO videojuegos (titulo, genero, plataforma, precio, stock, anio, descripcion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING {COL_JUEGO}""",
                (datos.titulo, datos.genero, datos.plataforma, datos.precio,
                 datos.stock, datos.anio, datos.descripcion),
            )
            return cur.fetchone()
    except errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Ya existe un videojuego con ese título")


@videojuegos.put("/{juego_id}")
def actualizar_juego(juego_id: int, datos: VideojuegoActualizar, admin: dict = Depends(solo_admin)):
    campos = datos.model_dump(exclude_unset=True)
    return actualizar_fila("videojuegos", juego_id, campos, PERM_JUEGO, COL_JUEGO)


@videojuegos.delete("/{juego_id}")
def eliminar_juego(juego_id: int, admin: dict = Depends(solo_admin)):
    with get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM videojuegos WHERE id = %s RETURNING id", (juego_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Videojuego no encontrado")
    return {"mensaje": "Videojuego eliminado (sus reseñas también)"}


# ---------- Reseñas ----------
@resenas.get("")
def listar_resenas(videojuego_id: Optional[int] = None, usuario: dict = Depends(usuario_actual)):
    with get_cursor() as cur:
        if videojuego_id:
            cur.execute(f"SELECT {COL_RESENA} FROM resenas WHERE videojuego_id = %s ORDER BY id", (videojuego_id,))
        else:
            cur.execute(f"SELECT {COL_RESENA} FROM resenas ORDER BY id")
        return cur.fetchall()


@resenas.post("", status_code=201)
def crear_resena(datos: ResenaCrear, admin: dict = Depends(solo_admin)):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                f"""INSERT INTO resenas (videojuego_id, autor, puntuacion, comentario)
                    VALUES (%s, %s, %s, %s) RETURNING {COL_RESENA}""",
                (datos.videojuego_id, datos.autor, datos.puntuacion, datos.comentario),
            )
            return cur.fetchone()
    except errors.ForeignKeyViolation:
        raise HTTPException(status_code=404, detail="El videojuego indicado no existe")


@resenas.put("/{resena_id}")
def actualizar_resena(resena_id: int, datos: ResenaActualizar, admin: dict = Depends(solo_admin)):
    campos = datos.model_dump(exclude_unset=True)
    return actualizar_fila("resenas", resena_id, campos, PERM_RESENA, COL_RESENA)


@resenas.delete("/{resena_id}")
def eliminar_resena(resena_id: int, admin: dict = Depends(solo_admin)):
    with get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM resenas WHERE id = %s RETURNING id", (resena_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Reseña no encontrada")
    return {"mensaje": "Reseña eliminada"}