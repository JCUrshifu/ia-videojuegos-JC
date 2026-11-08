from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.db import get_cursor
from app.deps import usuario_actual
from app.seguridad import crear_token, verificar_password

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    """Inicia sesión. En 'username' se escribe el correo electrónico."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, nombre, email, password_hash, rol, activo FROM usuarios WHERE email = %s",
            (form.username.strip().lower(),),
        )
        usuario = cur.fetchone()
    if not usuario or not verificar_password(form.password, usuario["password_hash"]):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    if not usuario["activo"]:
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    return {
        "access_token": crear_token(usuario["id"], usuario["rol"]),
        "token_type": "bearer",
        "rol": usuario["rol"],
        "nombre": usuario["nombre"],
    }


@router.get("/me")
def perfil(usuario: dict = Depends(usuario_actual)):
    """Datos del usuario que inició sesión."""
    return usuario


@router.post("/logout")
def logout(usuario: dict = Depends(usuario_actual)):
    """Cierra sesión. El token es sin estado: el cliente debe descartarlo."""
    return {"mensaje": "Sesión cerrada. Elimina el token en el cliente."}