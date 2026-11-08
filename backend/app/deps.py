from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.db import get_cursor
from app.seguridad import decodificar_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def usuario_actual(token: str = Depends(oauth2_scheme)) -> dict:
    """Devuelve el usuario dueño del token o responde 401."""
    datos = decodificar_token(token)
    if not datos:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, nombre, email, rol, activo, limite_tokens FROM usuarios WHERE id = %s",
            (int(datos["sub"]),),
        )
        usuario = cur.fetchone()
    if not usuario or not usuario["activo"]:
        raise HTTPException(
            status_code=401,
            detail="Usuario inexistente o desactivado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def solo_admin(usuario: dict = Depends(usuario_actual)) -> dict:
    """Permite el paso solo a administradores (si no, 403)."""
    if usuario["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador")
    return usuario