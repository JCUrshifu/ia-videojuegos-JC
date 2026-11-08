from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import JWT_SECRET

ALGORITMO = "HS256"
EXPIRA_HORAS = 8


def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def crear_token(usuario_id: int, rol: str) -> str:
    expira = datetime.now(timezone.utc) + timedelta(hours=EXPIRA_HORAS)
    datos = {"sub": str(usuario_id), "rol": rol, "exp": expira}
    return jwt.encode(datos, JWT_SECRET, algorithm=ALGORITMO)


def decodificar_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITMO])
    except JWTError:
        return None