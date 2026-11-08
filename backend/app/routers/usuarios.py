from fastapi import APIRouter, Depends, HTTPException
from psycopg2 import errors

from app.crud import actualizar_fila
from app.db import get_cursor
from app.deps import solo_admin
from app.schemas import UsuarioActualizar, UsuarioCrear
from app.seguridad import hashear_password

router = APIRouter(prefix="/usuarios", tags=["Usuarios (admin)"])

COLUMNAS = "id, nombre, email, rol, activo, limite_tokens, creado_en"
PERMITIDAS = {"nombre", "email", "password_hash", "rol", "activo", "limite_tokens"}


@router.get("")
def listar(admin: dict = Depends(solo_admin)):
    with get_cursor() as cur:
        cur.execute(f"SELECT {COLUMNAS} FROM usuarios ORDER BY id")
        return cur.fetchall()


@router.get("/{usuario_id}")
def obtener(usuario_id: int, admin: dict = Depends(solo_admin)):
    with get_cursor() as cur:
        cur.execute(f"SELECT {COLUMNAS} FROM usuarios WHERE id = %s", (usuario_id,))
        fila = cur.fetchone()
    if not fila:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return fila


@router.post("", status_code=201)
def crear(datos: UsuarioCrear, admin: dict = Depends(solo_admin)):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                f"""INSERT INTO usuarios (nombre, email, password_hash, rol, limite_tokens)
                    VALUES (%s, %s, %s, %s, %s) RETURNING {COLUMNAS}""",
                (datos.nombre, datos.email.lower(), hashear_password(datos.password),
                 datos.rol, datos.limite_tokens),
            )
            return cur.fetchone()
    except errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")


@router.put("/{usuario_id}")
def actualizar(usuario_id: int, datos: UsuarioActualizar, admin: dict = Depends(solo_admin)):
    campos = datos.model_dump(exclude_unset=True)
    if usuario_id == admin["id"] and (campos.get("activo") is False or campos.get("rol") == "usuario"):
        raise HTTPException(status_code=400, detail="No puedes desactivarte ni quitarte el rol de admin")
    if "password" in campos:
        campos["password_hash"] = hashear_password(campos.pop("password"))
    if "email" in campos:
        campos["email"] = campos["email"].lower()
    return actualizar_fila("usuarios", usuario_id, campos, PERMITIDAS, COLUMNAS)


@router.delete("/{usuario_id}")
def eliminar(usuario_id: int, admin: dict = Depends(solo_admin)):
    if usuario_id == admin["id"]:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    with get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM usuarios WHERE id = %s RETURNING id", (usuario_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"mensaje": "Usuario eliminado"}